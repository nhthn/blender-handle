import math
import random
import sys
import traceback

import bmesh
import mathutils
import bpy


bl_info = {
    "name": "Make Handle",
    "blender": (3, 3, 1),
    "category": "Mesh",
}


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


def rotate_list(the_list, n):
    return the_list[n:] + the_list[:n]


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
        while angle < last_angle:
            angle += 2 * math.pi
        result.append((radius, angle))
        last_angle = angle
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


def connect_vertices_with_prism(mesh, vertices_1, vertices_2):
    # Ensure vertices_1 has more vertices than vertices_2.
    if len(vertices_1) < len(vertices_2):
        connect_vertices_with_prism(mesh, vertices_2, vertices_1)
        return
    # Connect with quadrilaterals.
    for i in range(len(vertices_2)):
        vertices = [
            vertices_1[i],
            vertices_1[(i + 1) % len(vertices_1)],
            vertices_2[(i + 1) % len(vertices_2)],
            vertices_2[i],
        ]
        bmesh.ops.contextual_create(mesh, geom=vertices)
    # Connect with triangles.
    for i in range(len(vertices_2), len(vertices_1)):
        vertices = [
            vertices_1[i],
            vertices_1[(i + 1) % len(vertices_1)],
            vertices_2[0],
        ]
        bmesh.ops.contextual_create(mesh, geom=vertices)


def make_handle(mesh, face_1, vertex_1, face_2, vertex_2, num_segments, weight, twists=0):
    if vertex_1 not in face_1.verts:
        raise RuntimeError("Vertex 1 not in face 1")
    if vertex_2 not in face_2.verts:
        raise RuntimeError("Vertex 2 not in face 2")

    normal_1 = face_1.normal
    normal_2 = -face_2.normal

    centroid_1 = get_centroid(face_1)
    centroid_2 = get_centroid(face_2)

    original_vertices_1 = face_1.verts[:]
    shift_1 = original_vertices_1.index(vertex_1)
    original_vertices_1 = rotate_list(original_vertices_1, shift_1)

    original_vertices_2 = face_2.verts[:]
    original_vertices_2 = original_vertices_2[::-1]
    shift_2 = original_vertices_2.index(vertex_2)
    original_vertices_2 = rotate_list(original_vertices_2, shift_2)

    # Translate the two polygons so their centroids are the origin.
    points_1 = [vertex.co - centroid_1 for vertex in original_vertices_1]
    points_2 = [vertex.co - centroid_2 for vertex in original_vertices_2]

    # Extend the shorter of the two point lists with a duplicated point.
    if len(points_1) > len(points_2):
        points_2.extend([points_2[0]] * (len(points_1) - len(points_2)))
    elif len(points_2) > len(points_1):
        points_1.extend([points_1[0]] * (len(points_2) - len(points_1)))

    # Rotate the two polygons so their normals are the same vector. For some reason, that
    # vector is the displacement from one centroid to the other; not clear to me why.
    rotation_plane_normal = (centroid_2 - centroid_1).normalized()
    vertices_1 = rotate_polygon_to_new_normal(points_1, normal_1, rotation_plane_normal)
    vertices_2 = rotate_polygon_to_new_normal(points_2, normal_2, rotation_plane_normal)

    # We set up a 2D coordinate system in the plane orthogonal to rotation_plane_normal.
    # The exact choice isn't important, but they need to be orthogonal to each other and
    # to rotation_plane_normal. We retrieve the X-axis from one of the edges and the
    # Y-axis is produced with a cross product.
    # We ensure that the edge that we get the X-axis from is nondegenerate, i.e. its
    # length is not close to zero.
    for i in range(len(vertices_1)):
        displacement = vertices_1[(i - 1) % len(vertices_1)] - vertices_1[i]
        if displacement.length >= 1e-10:
            x_axis = displacement.normalized()
            break
    else:
        raise RuntimeError("All the vertices in one of the faces are bunched together")
    y_axis = rotation_plane_normal.cross(x_axis)

    # Project the two 3D polygons onto the plane and convert them to polar form using the
    # coordinate system.
    points_1_polar = convert_polygon_to_polar(vertices_1, x_axis, y_axis)
    points_2_polar = convert_polygon_to_polar(vertices_2, x_axis, y_axis)

    # If the angle of the first point of polygon 1 is more than 180 degrees from the angle
    # of the angle of the first point of polygon 2, the handle will have an extra twist.
    # Subtracting 2pi from all angles in polygon 2 will untwist it.
    if points_2_polar[0][1] - points_1_polar[0][1] > math.pi:
        points_2_polar = [
            (radius, angle - 2 * math.pi) for radius, angle in points_2_polar
        ]
    points_2_polar = [
        (radius, angle + 2 * math.pi * twists) for radius, angle in points_2_polar
    ]

    # Set up a 2D list of vertices. Each item of rings corresponds to a ring of vertices
    # forming a polygonal cross section of the handle. We will be creating new vertices
    # for every ring except the first and last, where we reuse existing vertices from the
    # two original faces.
    rings = [original_vertices_1]

    ts = [i / num_segments for i in range(1, num_segments)]
    for t in ts:
        # Use a cubic Hermite spline to get the centroid of the polygonal ring.
        centroid = get_handle_centroid(
            centroid_1, normal_1, centroid_2, normal_2, t, weight
        )
        # Use the derivative of that cubic Hermite spline to get the normal of the polygon.
        normal = get_handle_normal(
            centroid_1, normal_1, centroid_2, normal_2, t, weight
        )
        # Interpolate between the two 2D polar polygons and reconstruct a 3D polygon
        # orthogonal to the computed normal and centered on the computed centroid.
        polygon_polar = interpolate_polar_polygons(points_1_polar, points_2_polar, t)
        polygon = convert_polar_to_polygon(polygon_polar, x_axis, y_axis)
        polygon = rotate_polygon_to_new_normal(polygon, rotation_plane_normal, normal)
        polygon = [point + centroid for point in polygon]

        # Create vertices for each of the points.
        segment = []
        for point in polygon:
            new_vertex = bmesh.ops.create_vert(mesh, co=point)["vert"][0]
            segment.append(new_vertex)
        rings.append(segment)

    # Add the vertices from the second face.
    rings.append(original_vertices_2)

    # Connect the rings of vertices with quadrilaterals.
    for i in range(len(rings) - 1):
        connect_vertices_with_prism(mesh, rings[i], rings[i + 1])

    # Delete the original faces.
    bmesh.ops.delete(mesh, geom=[face_1], context="FACES_ONLY")
    bmesh.ops.delete(mesh, geom=[face_2], context="FACES_ONLY")


class MakeHandle(bpy.types.Operator):
    """Create a TopMod-style handle connecting two faces."""
    bl_idname = "mesh.make_handle"
    bl_label = "Make Handle"
    bl_options = {"REGISTER", "UNDO"}

    segments: bpy.props.IntProperty(name="Segments", default=10, min=1, soft_max=1000)
    weight: bpy.props.FloatProperty(name="Weight", default=10.0, soft_min=-1000.0, soft_max=1000.0)
    twists: bpy.props.IntProperty(name="Twists", default=0, soft_min=-10, soft_max=10)

    def execute(self, context):
        edit_mode_mesh = bpy.context.object.data
        mesh = bmesh.from_edit_mesh(edit_mode_mesh)
        faces = [
            element for element in mesh.select_history
            if isinstance(element, bmesh.types.BMFace)
        ]
        vertices = [
            element for element in mesh.select_history
            if isinstance(element, bmesh.types.BMVert)
        ]

        if len(faces) != 2:
            self.report({"WARNING"}, "Select exactly two faces")
            return {"CANCELLED"}
        if len(vertices) not in (1, 2):
            self.report({"WARNING"}, "Select 1 or 2 vertices")
            return {"CANCELLED"}

        face_1, face_2 = faces
        if len(vertices) == 1:
            vertex = vertices[0]
            if vertex not in face_1.verts and vertex not in face_2.verts:
                self.report({"WARNING"}, "Vertex is not in either of the selected faces")
                return {"CANCELLED"}
            if vertex not in face_1.verts or vertex not in face_2.verts:
                self.report({"WARNING"}, "One of the selected faces does not contain the vertex")
                return {"CANCELLED"}
            vertices = [vertex, vertex]

        vertex_1, vertex_2 = vertices

        if not (vertex_1 in face_1.verts or vertex_1 in face_2.verts):
            self.report({"WARNING"}, "One of the selected vertices is not adjacent to any face")
            return {"CANCELLED"}
        if not (vertex_2 in face_1.verts or vertex_2 in face_2.verts):
            self.report({"WARNING"}, "One of the selected vertices is not adjacent to any face")
            return {"CANCELLED"}
        if not (vertex_1 in face_1.verts or vertex_2 in face_1.verts):
            self.report({"WARNING"}, "One of the selected faces is not adjacent to any vertex")
            return {"CANCELLED"}
        if not (vertex_1 in face_2.verts or vertex_2 in face_2.verts):
            self.report({"WARNING"}, "One of the selected faces is not adjacent to any vertex")
            return {"CANCELLED"}

        if vertex_1 not in face_1.verts or vertex_2 not in face_2.verts:
            vertex_1, vertex_2 = vertex_2, vertex_1

        make_handle(
            mesh,
            face_1,
            vertex_1,
            face_2,
            vertex_2,
            self.segments,
            self.weight,
            self.twists,
        )
        bmesh.update_edit_mesh(edit_mode_mesh)
        return {"FINISHED"}


def make_handle_menu_func(self, context):
    self.layout.operator(MakeHandle.bl_idname)


def register():
    bpy.utils.register_class(MakeHandle)
    bpy.types.VIEW3D_MT_edit_mesh.append(make_handle_menu_func)


def unregister():
    bpy.utils.unregister_class(MakeHandle)
    bpy.types.VIEW3D_MT_edit_mesh.remove(make_handle_menu_func)


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    bpy.ops.mesh.primitive_cube_add()

    bpy_mesh = bpy.context.object.data
    mesh = bmesh.new()
    mesh.from_mesh(bpy_mesh)
    mesh.faces.ensure_lookup_table()

    face_to_remove = mesh.faces[0]
    face_1 = mesh.faces[1]
    vertices = face_to_remove.verts[:]
    bmesh.ops.delete(mesh, geom=[face_to_remove], context="FACES_ONLY")

    face_2 = mesh.faces.new([vertices[0], vertices[1], vertices[2]])
    mesh.faces.new([vertices[0], vertices[2], vertices[3]])

    mesh.normal_update()

    vertex_1 = face_1.verts[0]
    vertex_2 = face_2.verts[0]

    make_handle(
        mesh, face_1, vertex_1, face_2, vertex_2, 10, 30.0
    )

    mesh.to_mesh(bpy_mesh)
    mesh.free()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
