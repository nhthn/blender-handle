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


def rotate_face_to_new_normal(vertices, old_normal, new_normal):
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
    sin_angle = axis.length
    cos_angle = old_normal_normalized.dot(new_normal_normalized)
    angle = math.atan2(sin_angle, cos_angle)
    quaternion = mathutils.Quaternion(axis, angle)
    return [quaternion.to_matrix() @ vertex for vertex in vertices]


def get_handle_centroid(centroid_1, normal_1, centroid_2, normal_2, t, weight):
    """Given the centroids and normals of two faces, compute the centroid of an
    intermediate face parametrized by the variable 0 <= t <= 1. The weight parameter
    controls how much the handle sticks out."""
    return (
        centroid_1 * hermite_1(t)
        + centroid_2 * hermite_1(1 - t)
        + weight * normal_1 * hermite_2(t)
        + weight * normal_2 * hermite_2(1 - t)
    )


def get_handle_normal(centroid_1, normal_1, centroid_2, normal_2, t, weight):
    """Like get_handle_centroid, but compute the normal of the face instead of the
    centroid. This is accomplished by taking the derivative of get_handle_centroid
    and then normalizing the resulting 3D vector."""
    return (
        centroid_1 * hermite_1_derivative(t)
        + centroid_2 * -hermite_1_derivative(1 - t)
        + weight * normal_1 * hermite_2_derivative(t)
        + weight * normal_2 * -hermite_2_derivative(1 - t)
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

    centroid_1 = get_centroid(face_1)
    centroid_2 = get_centroid(face_2)
    # vertices_1 = [vertex.co - centroid_1 for vertex in face_1.verts]
    # vertices_2 = [vertex.co - centroid_2 for vertex in face_2.verts]
    # rotation_plane_normal = (centroid_2 - centroid_1).normalized()
    # vertices_1 = rotate_face_to_new_normal(vertices_1, rotation_plane_normal)
    # vertices_2 = rotate_face_to_new_normal(vertices_2, rotation_plane_normal)

    weight = 30
    n = 10
    ts = [i / (n - 1) for i in range(n)]
    for t in ts:
        centroid = get_handle_centroid(
            centroid_1, face_1.normal, centroid_2, face_2.normal, t, weight
        )
        normal = get_handle_normal(
            centroid_1, face_1.normal, centroid_2, face_2.normal, t, weight
        )
        y = normal.cross(mathutils.Vector([1, 0, 0])).normalized()
        x = y.cross(normal)
        num_points = 10
        for i in range(num_points):
            angle = i * 2 * math.pi / num_points
            point = centroid + x * math.cos(angle) + y * math.sin(angle)
            bmesh.ops.create_vert(mesh, co=point)

    mesh.to_mesh(bpy_mesh)
    mesh.free()



if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
