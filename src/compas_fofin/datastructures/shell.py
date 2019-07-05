from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from compas.datastructures import Mesh
from compas.utilities import pairwise


class Shell(Mesh):
    """:class:`Shell` extends the mesh datastructure
    with attributes and methods related to form finding (and analysis) of shells.

    Attributes
    ----------
    default_vertex_attributes : dict
        The default data attributes assigned to every new vertex.

        * ``'px' = 0.0`` : Component of an externally applied load along the X axis.
        * ``'py' = 0.0`` : Component of an externally applied load along the Y axis.
        * ``'pz' = 0.0`` : Component of an externally applied load along the Z axis.
        * ``'rx' = 0.0`` : Component of an unbalanced (residual) force along the X axis.
        * ``'ry' = 0.0`` : Component of an unbalanced (residual) force along the Y axis.
        * ``'rz' = 0.0`` : Component of an unbalanced (residual) force along the Z axis.
        * ``'t' = 0.0`` : Thickness of the shell at the vertex.
        * ``'is_anchor' = False`` : Indicate that a vertex is anchored and can take reaction forces in XYZ.
        * ``'is_fixed' = False`` : Can be used to mark a vertex as "fixed" during geometrical operations such as smoothing.
        * ``'constraint' = None`` : Can be used to store the name or ID of a geometrical object to which a vertex is constrained.
        * ``'param' = None`` : Stores the current parameter of a vertex on the constraint object.

    default_edge_attributes : dict
        The default data attributes assigned to every new edge.

        * ``'q'`` : ``0.0``
        * ``'f'`` : ``0.0``
        * ``'l'`` : ``0.0``
        * ``'E'`` : ``0.0``
        * ``'r'`` : ``0.0``
        * ``'l0'`` : ``0.0``

    Notes
    -----

    """

    def __init__(self):
        super(Shell, self).__init__()
        self.attributes.update({
            'color.forces:compression' : (0, 0, 255),
            'color.forces:tension'     : (255, 0, 0),
            'color.reactions'          : (0, 255, 0),
            'color.residuals'          : (0, 255, 255),
            'color.loads'              : (0, 0, 255),
            'scale.forces'             : 0.1,
            'scale.reactions'          : 1.0,
            'scale.residuals'          : 1.0,
            'scale.loads'              : 1.0,
            'tol.reactions'            : 1e-3,
            'tol.residuals'            : 1e-3,
            'tol.forces'               : 1e-3,

            'density' : 1.0,
        })
        self.default_vertex_attributes.update({
            'x' : 0.0,
            'y' : 0.0,
            'z' : 0.0,
            'px' : 0.0,
            'py' : 0.0,
            'pz' : 0.0,
            'rx' : 0.0,
            'ry' : 0.0,
            'rz' : 0.0,
            't' : 0.0,
            'is_anchor' : False,
            'is_fixed'  : False,
            'constraint': None,
            'param'     : None,
        })
        self.default_edge_attributes.update({
            'q' : 1.0,
            'f' : 0.0,
            'l' : 0.0,
            'E' : 0.0,
            'r' : 0.0,
            'l0' : 0.0,
            'is_edge' : True,
        })
        self.default_face_attributes.update({
            'strip' : None
        })

    @classmethod
    def from_lines(cls, lines):
        """Make a shell from a Rhino mesh."""
        return super(Shell, cls).from_lines(lines, delete_boundary_face=False)

    @classmethod
    def from_rhinomesh(cls, guid):
        """Make a shell from a Rhino mesh."""
        from compas_rhino.helpers import mesh_from_guid
        return mesh_from_guid(cls, guid)

    @classmethod
    def from_rhinosurface(cls, guid, u=10, v=10):
        """Make a mesh from a Rhino surface."""
        from compas_rhino.helpers import mesh_from_surface_uv
        return mesh_from_surface_uv(cls, guid, density=(u, v))

    def get_continuous_edges(self, edge, directed=True):
        """Get the edges forming a continuous line with the selected edge."""
        boundary = set(self.vertices_on_boundary())
        edges = [edge]
        u, v = edge
        end = v
        while True:
            if self.vertex_degree(u) != 4:
                break
            if u == end:
                break
            if u in boundary:
                break
            nbrs = self.vertex_neighbors(u, ordered=True)
            i = nbrs.index(v)
            v = nbrs[i - 2]
            edges.append((u, v))
            u, v = v, u
        v, u = edge
        end = v
        while True:
            if self.vertex_degree(u) != 4:
                break
            if u == end:
                break
            if u in boundary:
                break
            nbrs = self.vertex_neighbors(u, ordered=True)
            i = nbrs.index(v)
            v = nbrs[i - 2]
            edges.append((u, v))
            u, v = v, u
        if not directed:
            return edges
        edgeset = set(list(self.edges()))
        return [(u, v) if (u, v) in edgeset else (v, u) for u, v in edges]

    def get_parallel_edges(self, edge):
        """Get the edges parallel to the selected edge."""
        edges = [edge]
        u, v = edge
        while True:
            face = self.halfedge[u][v]
            if face is None:
                break
            vertices = self.face_vertices(face)
            if len(vertices) != 4:
                break
            i = vertices.index(u)
            u = vertices[i - 1]
            v = vertices[i - 2]
            if u in edge and v in edge:
                break
            edges.append((u, v))
        edges[:] = edges[::-1]
        v, u = edge
        while True:
            face = self.halfedge[u][v]
            if face is None:
                break
            vertices = self.face_vertices(face)
            if len(vertices) != 4:
                break
            i = vertices.index(u)
            u = vertices[i - 1]
            v = vertices[i - 2]
            if u in edge and v in edge:
                break
            edges.append((u, v))
        directed = set(list(self.edges()))
        return [(u, v) if (u, v) in directed else (v, u) for u, v in edges]

    def get_face_strip(self, fkey):
        faces = []
        boundary = set(self.faces_on_boundary())
        if fkey not in boundary:
            return faces
        vertices = self.face_vertices(fkey)
        if len(vertices) != 4:
            return faces
        for u, v in pairwise(vertices + vertices[:1]):
            nbr = self.halfedge[v][u]
            if nbr is None:
                edge = u, v
                break
            edge = None
        if not edge:
            return faces
        i = vertices.index(edge[0])
        u = vertices[i - 2]
        v = vertices[i - 1]
        faces.append(fkey)
        while True:
            fkey = self.halfedge[v][u]
            if fkey is None:
                break
            v, u = u, v
            faces.append(fkey)
            vertices = self.face_vertices(fkey)
            if len(vertices) != 4:
                break
            i = vertices.index(u)
            u = vertices[i - 2]
            v = vertices[i - 1]
        return faces

    def draw(self, layer=None, clear_layer=True, settings=None):
        from compas_fofin.rhino import ShellArtist
        layer = layer or settings.get('layer')
        artist = ShellArtist(self, layer=layer)
        if clear_layer:
            artist.clear_layer()
        if settings.get('show.vertices', True):
            vertexcolor = {}
            vertexcolor.update({key: (0, 255, 0) for key in self.vertices_where_predicate(lambda key, attr: attr['constraint'] is not None)})
            vertexcolor.update({key: (255, 0, 0) for key in self.vertices_where({'is_anchor': True})})
            artist.draw_vertices(color=vertexcolor)
        if settings.get('show.edges', True):
            artist.draw_edges()
        if settings.get('show.faces', True):
            artist.draw_faces()
        if settings.get('show.forces', False):
            artist.draw_forces(
                compression=settings.get('color.forces:compression', None),
                tension=settings.get('color.forces:tension', None),
                scale=settings.get('scale.forces', None))
        if settings.get('show.reactions', False):
            artist.draw_reactions(
                color=settings.get('color.reactions', None),
                scale=settings.get('scale.reactions', None))
        if settings.get('show.residuals', False):
            artist.draw_reactions(
                color=settings.get('color.residuals', None),
                scale=settings.get('scale.residuals', None))
        if settings.get('show.loads', False):
            artist.draw_loads(
                color=settings.get('color.loads', None),
                scale=settings.get('scale.loads', None))
        artist.redraw()


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    pass
