import math
import sys
import traceback

import bmesh
import bpy
import mathutils


def hermite_1(t):
    """The unique cubic such that f(0) = 1, f(1) = 0, f'(0) = f'(1) = 0."""
    return 2 * t * t * t - 3 * t * t + 1


def hermite_2(t):
    """The unique cubic such that f(0) = f(1) = 0, f'(0) = 1, f'(1) = 0."""
    return t * t * t - 2 * t * t + t


def hermite_1_derivative(t):
    """Derivative of the function hermite_1."""
    return 3 * 2 * t * t - 2 * 3 * t


def hermite_2_derivative(t):
    """Derivative of the function hermite_2."""
    return 3 * t * t - 2 * 2 * t + 1


def get_centroid(face):
    """Compute the centroid of a face."""
    result = mathutils.Vector()
    for vertex in face.verts:
        result += vertex.co
    return result / len(face.verts)


def rotate_polygon_to_new_normal(vertices, old_normal, new_normal):
    """Given a set of vertex coordinates, a face normal and a new normal, return
    a new set of vertex coordinates that are rotated so the normal matches the new
    normal."""
    old_normal_normalized = old_normal.normalized()
    new_normal_normalized = new_normal.normalized()
    axis = old_normal_normalized.cross(new_normal_normalized)
    if axis.length_squared < 1e-3:
        # If the cross product is close to a zero vector, the old and new normals
        # are either nearly identical or in opposite directions.
        return vertices[:]
    cos_angle = old_normal_normalized.dot(new_normal_normalized)
    sin_angle = axis.length
    angle = math.atan2(sin_angle, cos_angle)
    quaternion = mathutils.Quaternion(axis, angle)
    return [quaternion.to_matrix() @ vertex for vertex in vertices]


def convert_polygon_to_polar(vertices, x_axis, y_axis):
    """Project the given vertices on to the plane formed by the given x-axis and y-axis
    and represent them in polar form."""
    result = []
    last_angle = 0.0
    for vertex in vertices:
        cos_angle = vertex.dot(x_axis)
        sin_angle = vertex.dot(y_axis)
        radius = vertex.length
        angle = math.atan2(sin_angle, cos_angle)
        if angle < last_angle:
            angle += 2 * math.pi
        result.append((radius, angle))
    return result


def convert_polar_to_polygon(polar_polygon, x_axis, y_axis):
    result = []
    for radius, angle in polar_polygon:
        point = radius * (x_axis * math.cos(angle) + y_axis * math.sin(angle))
        result.append(point)
    return result


def interpolate_polar_polygons(polar_polygon_1, polar_polygon_2, t):
    result = []
    for i in range(len(polar_polygon_1)):
        result.append((
            polar_polygon_1[i][0] * (1 - t) + polar_polygon_2[i][0] * t,
            polar_polygon_1[i][1] * (1 - t) + polar_polygon_2[i][1] * t
        ))
    return result


def get_handle_centroid(centroid_1, normal_1, centroid_2, normal_2, t, weight):
    """Given the centroids and normals of two faces, compute the centroid of an
    intermediate face parametrized by the variable 0 <= t <= 1. The weight parameter
    controls how much the handle sticks out."""
    return (
        centroid_1 * hermite_1(t)
        + centroid_2 * hermite_1(1 - t)
        + weight * normal_1 * hermite_2(t)
        - weight * normal_2 * hermite_2(1 - t)
    )


def get_handle_normal(centroid_1, normal_1, centroid_2, normal_2, t, weight):
    """Like get_handle_centroid, but compute the normal of the face instead of the
    centroid. This is accomplished by taking the derivative of get_handle_centroid
    and then normalizing the resulting 3D vector."""
    return (
        centroid_1 * hermite_1_derivative(t)
        + centroid_2 * -hermite_1_derivative(1 - t)
        + weight * normal_1 * hermite_2_derivative(t)
        - weight * normal_2 * -hermite_2_derivative(1 - t)
    ).normalized()


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    bpy.ops.mesh.primitive_cube_add()

    bpy_mesh = bpy.context.object.data
    mesh = bmesh.new()
    mesh.from_mesh(bpy_mesh)

    faces = mesh.faces[:]
    face_1 = faces[0]
    face_2 = faces[1]

    normal_1 = face_1.normal
    normal_2 = -face_2.normal

    centroid_1 = get_centroid(face_1)
    centroid_2 = get_centroid(face_2)
    points_1 = [vertex.co - centroid_1 for vertex in face_1.verts]
    points_2 = [vertex.co - centroid_2 for vertex in face_2.verts]
    points_2 = points_2[::-1]
    if len(points_1) != len(points_2):
        raise RuntimeError("Polygons must have same number of sides")
    rotation_plane_normal = (centroid_2 - centroid_1).normalized()
    vertices_1 = rotate_polygon_to_new_normal(points_1, normal_1, rotation_plane_normal)
    vertices_2 = rotate_polygon_to_new_normal(points_2, normal_2, rotation_plane_normal)
    x_axis = (vertices_1[-1] - vertices_1[0]).normalized()
    y_axis = rotation_plane_normal.cross(x_axis)
    points_1_polar = convert_polygon_to_polar(vertices_1, x_axis, y_axis)
    points_2_polar = convert_polygon_to_polar(vertices_2, x_axis, y_axis)
    if points_2_polar[0][1] - points_1_polar[0][1] > math.pi:
        points_2_polar = [
            (radius, angle - 2 * math.pi) for radius, angle in points_2_polar
        ]

    handle_vertices = [face_1.verts]

    weight = 30
    n = 10
    ts = [i / (n - 1) for i in range(1, n - 1)]
    for t in ts:
        centroid = get_handle_centroid(
            centroid_1, normal_1, centroid_2, normal_2, t, weight
        )
        normal = get_handle_normal(
            centroid_1, normal_1, centroid_2, normal_2, t, weight
        )
        polygon_polar = interpolate_polar_polygons(points_1_polar, points_2_polar, t)
        polygon = convert_polar_to_polygon(polygon_polar, x_axis, y_axis)
        polygon = rotate_polygon_to_new_normal(polygon, rotation_plane_normal, normal)
        polygon = [point + centroid for point in polygon]
        segment = []
        for point in polygon:
            new_vertex = bmesh.ops.create_vert(mesh, co=point)["vert"][0]
            segment.append(new_vertex)
        handle_vertices.append(segment)

    handle_vertices.append(face_2.verts[:][::-1])

    for i in range(len(handle_vertices) - 1):
        segment_1 = handle_vertices[i]
        segment_2 = handle_vertices[i + 1]
        for j in range(len(segment_1)):
            vertices = [
                segment_1[j],
                segment_1[(j + 1) % len(segment_1)],
                segment_2[(j + 1) % len(segment_2)],
                segment_2[j],
            ]
            bmesh.ops.contextual_create(mesh, geom=vertices)

    bmesh.ops.delete(mesh, geom=[face_1], context="FACES_ONLY")
    bmesh.ops.delete(mesh, geom=[face_2], context="FACES_ONLY")

    mesh.to_mesh(bpy_mesh)
    mesh.free()



if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
