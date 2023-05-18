"""Discrete Surfaces with Elastic metrics.

Lead authors: Emmanuel Hartman, Adele Myers.
"""
import math

import geomstats.backend as gs
from geomstats.geometry.euclidean import Euclidean
from geomstats.geometry.manifold import Manifold
from geomstats.geometry.riemannian_metric import RiemannianMetric


class DiscreteSurfaces(Manifold):
    r"""Space of parameterized discrete surfaces.

    Each surface is sampled with fixed n_vertices vertices and n_faces faces
    in $\mathbb{R}^3$.

    Each individual surface is represented by a 2d-array of shape `[
    n_vertices, 3]`. This space corresponds to the space of immersions
    defined below, i.e. the
    space of smooth functions from a template to manifold $M$ into  $\mathbb{R}^3$,
    with non-vanishing Jacobian.
    .. math::
        Imm(M,\mathbb{R}^3)=\{ f \in C^{\infty}(M, \mathbb{R}^3)
        \|Df(x)\|\neq 0 \forall x \in M \}.

    Parameters
    ----------
    faces : integer array-like, shape=[n_faces, 3]
        Triangulation of the surface.
        Each face is given by 3 indices that indicate its vertices.
    """

    def __init__(self, faces):
        ambient_dim = 3
        self.ambient_manifold = Euclidean(dim=ambient_dim)
        self.faces = faces
        self.n_faces = len(faces)
        self.n_vertices = int(gs.amax(self.faces) + 1)
        self.shape = (self.n_vertices, ambient_dim)
        super().__init__(
            dim=self.n_vertices * ambient_dim,
            shape=(self.n_vertices, 3),
        )

    def belongs(self, point, atol=gs.atol):
        """Evaluate whether a point belongs to the manifold.

        Checks that vertices are inputed in proper form and are
        consistent with the mesh structure.

        Parameters
        ----------
        point : array-like, shape=[..., n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation.
        atol : float
            Absolute tolerance.
            Optional, default: backend atol.

        Returns
        -------
        belongs : array-like, shape=[...,]
            Boolean evaluating if point belongs to the space of discrete
            surfaces.
        """
        belongs = self.shape == point.shape[-self.point_ndim :]
        shape = point.shape[: -self.point_ndim]
        if belongs:
            return gs.ones(shape, dtype=bool)
        return gs.zeros(shape, dtype=bool)

    def is_tangent(self, vector, base_point, atol=gs.atol):
        """Check whether the vector is tangent at base_point.

        Tangent vectors are identified with points of the vector space so
        this checks the shape of the input vector.

        Parameters
        ----------
        vector : array-like, shape=[..., n_vertices, 3]
            Vector, i.e. a 3D vector field on the surface.
        base_point : array-like, shape=[..., n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation.
        atol : float
            Absolute tolerance.
            Optional, default: backend atol.

        Returns
        -------
        is_tangent : array-like, shape=[...,]
            Boolean denoting if vector is a tangent vector at the base point.
        """
        belongs = self.belongs(vector, atol)
        if base_point is not None and base_point.ndim > vector.ndim:
            return gs.broadcast_to(belongs, base_point.shape[: -self.point_ndim])
        return belongs

    def to_tangent(self, vector, base_point):
        """Project a vector to a tangent space of the manifold.

        Parameters
        ----------
        vector : array-like, shape=[..., n_vertices, 3]
            Vector, i.e. a 3D vector field on the surface.
        base_point : array-like, shape=[..., n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        tangent_vec : array-like, shape=[..., *point_shape]
            Tangent vector at base point.
        """
        return gs.copy(vector)

    def projection(self, point):
        """Project a point to the manifold.

        Parameters
        ----------
        point : array-like, shape=[..., n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation..

        Returns
        -------
        _ : array-like, shape=[..., n_vertices, 3]
            Point.
        """
        return gs.copy(point)

    def random_point(self, n_samples=1):
        """Sample discrete surfaces.

        This sample random discrete surfaces with the correct number of vertices.

        Parameters
        ----------
        n_samples : int
            Number of surfaces to sample.
            Optional, Default=1

        Returns
        -------
        vertices : array-like, shape=[n_samples, n_vertices, 3]
            Vertices for a batch of points in the space of discrete surfaces.
        """
        vertices = self.ambient_manifold.random_point(n_samples * self.n_vertices)
        vertices = gs.reshape(vertices, (n_samples, self.n_vertices, 3))
        return vertices[0] if n_samples == 1 else vertices

    def _vertices(self, point):
        """Extract 3D vertices coordinates corresponding to each face.

        Parameters
        ----------
        point : array-like, shape=[..., n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        vertices : tuple of vertex_0, vertex_1, vertex_2 where:
            vertex_i : array-like, shape=[..., n_faces, 3]
                3D coordinates of the ith vertex of that face.
        """
        vertex_0, vertex_1, vertex_2 = tuple(
            gs.take(point, indices=self.faces[:, i], axis=-2) for i in range(3)
        )
        if point.ndim == 3 and vertex_0.ndim == 2:
            vertex_0 = gs.expand_dims(vertex_0, axis=0)
            vertex_1 = gs.expand_dims(vertex_1, axis=0)
            vertex_2 = gs.expand_dims(vertex_2, axis=0)
        return vertex_0, vertex_1, vertex_2

    def _triangle_areas(self, point):
        """Compute triangle areas for each face of the surface.

        Heron's formula gives the triangle's area in terms of its sides a b c:,
        As the square root of the product s(s - a)(s - b)(s - c),
        where s is the semiperimeter of the triangle s = (a + b + c)/2.

        Parameters
        ----------
        point : array-like, shape=[..., n_vertices, 3]
             Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        _ : array-like, shape=[..., n_faces, 1]
            Triangle area of each face.
        """
        vertex_0, vertex_1, vertex_2 = self._vertices(point)
        len_edge_12 = gs.linalg.norm((vertex_1 - vertex_2), axis=-1)
        len_edge_02 = gs.linalg.norm((vertex_0 - vertex_2), axis=-1)
        len_edge_01 = gs.linalg.norm((vertex_0 - vertex_1), axis=-1)
        half_perimeter = 0.5 * (len_edge_12 + len_edge_02 + len_edge_01)
        return gs.sqrt(
            (
                half_perimeter
                * (half_perimeter - len_edge_12)
                * (half_perimeter - len_edge_02)
                * (half_perimeter - len_edge_01)
            ).clip(min=1e-6)
        )

    def vertex_areas(self, point):
        """Compute vertex areas for a triangulated surface.

        Vertex area is the area of all of the triangles who are in contact (incident)
        with a specific vertex, according to the formula:
        vertex_areas = 2 * sum_incident_areas / 3.0

        Parameters
        ----------
        point : array-like, shape=[..., n_vertices, 3]
             Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        vertex_areas :  array-like, shape=[..., n_vertices, 1]
            Vertex area for each vertex.
        """
        batch_shape = point.shape[:-2]
        n_vertices = point.shape[-2]
        n_faces = self.faces.shape[0]
        area = self._triangle_areas(point)
        id_vertices = gs.broadcast_to(
            gs.flatten(self.faces), batch_shape + (math.prod(self.faces.shape),)
        )
        incident_areas = gs.zeros(batch_shape + (n_vertices,))
        val = gs.reshape(
            gs.broadcast_to(gs.expand_dims(area, axis=-2), batch_shape + (3, n_faces)),
            batch_shape + (-1,),
        )
        incident_areas = gs.scatter_add(
            incident_areas, dim=len(batch_shape), index=id_vertices, src=val
        )
        vertex_areas = 2 * incident_areas / 3.0
        return vertex_areas

    def normals(self, point):
        """Compute normals at each face of a triangulated surface.

        Normals are the cross products between edges of each face
        that are incident to its x-coordinate.

        Parameters
        ----------
        point : array-like, shape=[n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        normals_at_point : array-like, shape=[n_facesx1]
            Normals of each face of the mesh.
        """
        vertex_0, vertex_1, vertex_2 = self._vertices(point)
        normals_at_point = 0.5 * gs.cross(vertex_1 - vertex_0, vertex_2 - vertex_0)
        return normals_at_point

    def surface_one_forms(self, point):
        """Compute the vector valued one-forms.

        The one forms are evaluated at the faces of a triangulated surface.

        A one-form is represented by the two vectors (01) and (02) at each face
        of vertices 0, 1, 2.

        Parameters
        ----------
        point : array-like, shape=[..., n_vertices, 3]
             Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        one_forms_base_point : array-like, shape=[..., n_faces, 2, 3]
            One form evaluated at each face of the triangulated surface.
        """
        vertex_0, vertex_1, vertex_2 = self._vertices(point)
        one_forms = gs.stack([vertex_1 - vertex_0, vertex_2 - vertex_0], axis=-2)
        return one_forms

    def face_areas(self, point):
        """Compute the areas for each face of a triangulated surface.

        The corresponds to the volume area for the surface metric, that is
        the volume area of the pullback metric of the immersion defining the
        surface metric.

        Parameters
        ----------
        point : array-like, shape=[n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        _ : array-like, shape=[n_faces,]
            Area computed at each face of the triangulated surface.
        """
        surface_metrics = self.surface_metric_matrices(point)
        return gs.sqrt(gs.linalg.det(surface_metrics))

    def _surface_metric_matrices_from_one_forms(self, one_forms):
        """Compute the surface metric matrices directly from the one_forms.

        This function is useful for efficiency purposes.

        Parameters
        ----------
        one_forms : array-like, shape=[..., n_faces, 2, 3]
            One form evaluated at each face of the triangulated surface.

        Returns
        -------
        metric_mats : array-like, shape=[n_faces, 2, 2]
            Surface metric matrices evaluated at each face of
            the triangulated surface.
        """
        ndim = one_forms.ndim
        transpose_axes = tuple(range(ndim - 2)) + tuple(reversed(range(ndim - 2, ndim)))
        transposed_one_forms = gs.transpose(one_forms, axes=transpose_axes)
        return gs.matmul(one_forms, transposed_one_forms)

    def surface_metric_matrices(self, point):
        """Compute the surface metric matrices.

        The matrices are evaluated at the faces of a triangulated surface.

        The surface metric is the pullback metric of the immersion q
        defining the surface, i.e. of
        the map q: M -> R3, where M is the parameterization manifold.

        Parameters
        ----------
        point : array like, shape=[n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        metric_mats : array-like, shape=[n_faces, 2, 2]
            Surface metric matrices evaluated at each face of
            the triangulated surface.
        """
        one_forms = self.surface_one_forms(point)

        return self._surface_metric_matrices_from_one_forms(one_forms)

    def laplacian(self, point):
        r"""Compute the mesh Laplacian operator of a triangulated surface.

        Denoting q the surface, i.e. the point in the DiscreteSurfaces manifold,
        the laplacian at q is defined as the operator:
        :math: `\Delta_q = - Tr(g_q^{-1} \nabla^2)`
        where :math:`g_q` is the surface metric matrix of :math:`q`.

        Parameters
        ----------
        point :  array-like, shape=[n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        _laplacian : callable
            Function that evaluates the mesh Laplacian operator at a
            tangent vector field to the surface.
        """
        n_vertices, n_faces = point.shape[-2], self.faces.shape[0]
        vertex_0, vertex_1, vertex_2 = self._vertices(point)
        len_edge_12 = gs.linalg.norm((vertex_1 - vertex_2), axis=-1)
        len_edge_02 = gs.linalg.norm((vertex_0 - vertex_2), axis=-1)
        len_edge_01 = gs.linalg.norm((vertex_0 - vertex_1), axis=-1)

        half_perimeter = 0.5 * (len_edge_12 + len_edge_02 + len_edge_01)
        area = gs.sqrt(
            (
                half_perimeter
                * (half_perimeter - len_edge_12)
                * (half_perimeter - len_edge_02)
                * (half_perimeter - len_edge_01)
            ).clip(min=1e-6)
        )
        sq_len_edge_12, sq_len_edge_02, sq_len_edge_01 = (
            len_edge_12 * len_edge_12,
            len_edge_02 * len_edge_02,
            len_edge_01 * len_edge_01,
        )
        cot_12 = (sq_len_edge_02 + sq_len_edge_01 - sq_len_edge_12) / area
        cot_02 = (sq_len_edge_12 + sq_len_edge_01 - sq_len_edge_02) / area
        cot_01 = (sq_len_edge_12 + sq_len_edge_02 - sq_len_edge_01) / area
        cot = gs.stack([cot_12, cot_02, cot_01], axis=1)
        cot /= 2.0
        id_vertices_120 = self.faces[:, [1, 2, 0]]
        id_vertices_201 = self.faces[:, [2, 0, 1]]
        id_vertices = gs.reshape(
            gs.stack([id_vertices_120, id_vertices_201], axis=0), (2, n_faces * 3)
        )

        def _laplacian(tangent_vec):
            """Evaluate the mesh Laplacian operator.

            The operator is evaluated at a tangent vector at point to the
            manifold of DiscreteSurfaces. In other words, the operator is
            evaluated at a vector field defined on the surface point.

            Parameters
            ----------
            tangent_vec : array-like, shape=[..., n_vertices, 3]
                Tangent vector to the manifold at the base point that is the
                triangulated surface. This tangent vector is a vector field
                on the triangulated surface.

            Returns
            -------
            laplacian_at_tangent_vec: array-like, shape=[..., n_vertices, 3]
                Mesh Laplacian operator of the triangulated surface applied
                to one its tangent vector tangent_vec.
            """
            to_squeeze = False
            if tangent_vec.ndim == 2:
                tangent_vec = gs.expand_dims(tangent_vec, axis=0)
                to_squeeze = True
            n_tangent_vecs = len(tangent_vec)
            tangent_vec_diff = (
                tangent_vec[:, id_vertices[0]] - tangent_vec[:, id_vertices[1]]
            )
            values = gs.einsum(
                "bd,nbd->nbd", gs.stack([gs.flatten(cot)] * 3, axis=1), tangent_vec_diff
            )

            laplacian_at_tangent_vec = gs.zeros((n_tangent_vecs, n_vertices, 3))
            id_vertices_201_repeated = gs.tile(id_vertices[1, :], (n_tangent_vecs, 1))

            for i_dim in range(3):
                laplacian_at_tangent_vec[:, :, i_dim] = gs.scatter_add(
                    input=laplacian_at_tangent_vec[:, :, i_dim],
                    dim=1,
                    index=id_vertices_201_repeated,
                    src=values[:, :, i_dim],
                )
            return (
                gs.squeeze(laplacian_at_tangent_vec, axis=0)
                if to_squeeze
                else laplacian_at_tangent_vec
            )

        return _laplacian


class ElasticMetric(RiemannianMetric):
    """Elastic metric defined by a family of second order Sobolev metrics.

    Each individual discrete surface is represented by a 2D-array of shape `[
    n_vertices, 3]`. See [HSKCB2022]_ for details.

    Parameters
    ----------
    space : DiscreteSurfaces
        Instantiated DiscreteSurfaces manifold.
    a0 : float
        First order parameter.
    a1 : float
        Stretching parameter.
    b1 : float
        Shearing parameter.
    c1 : float
        Bending parameter.
    d1 : float
        Additonal first order parameter.
    a2 : float
        Second order parameter.

    References
    ----------
    .. [HSKCB2022] "Elastic shape analysis of surfaces with second-order
        Sobolev metrics: a comprehensive numerical framework".
        arXiv:2204.04238 [cs.CV], 25 Sep 2022
    """

    def __init__(self, space, a0, a1, b1, c1, d1, a2):
        super().__init__(dim=space.dim, shape=space.shape)
        self.space = space
        self.a0 = a0
        self.a1 = a1
        self.b1 = b1
        self.c1 = c1
        self.d1 = d1
        self.a2 = a2

    def inner_product(self, tangent_vec_a, tangent_vec_b, base_point):
        r"""Inner product between two tangent vectors at a base point.

        The inner-product has 6 terms, where each term corresponds to
        one of the 6 hyperparameters a0, a1, b1, c1, d1, a2.

        We denote h and k the tangent vectors a and b respectively.
        We denote q the base point, i.e. the surface.

        The six terms of the inner-product are given by:
        :math:`\int_M (G_{a_0} + G_{a_1} + G_{b_1} + G_{c_1} + G_{d_1} + G_{a_2})vol_q`

        where:
        - :math:`G_{a_0} = a_0 <h, k>`
        - :math:`G_{a_1} = a_1.g_q^{-1} <dh_m, dk_m>`
        - :math:`G_{b_1} = b_1.g_q^{-1} <dh_+, dk_+>`
        - :math:`G_{c_1} = c_1.g_q^{-1} <dh_\perp, dk_\perp>`
        - :math:`G_{d_1} = d_1.g_q^{-1} <dh_0, dk_0>`
        - :math:`G_{a_2} = a_2 <\Delta_q h, \Delta_q k>`

        with notations taken form .. [HSKCB2022].

        Parameters
        ----------
        tangent_vec_a: array-like, shape=[..., n_vertices, 3]
            Tangent vector at base point.
        tangent_vec_b: array-like, shape=[..., n_vertices, 3]
            Tangent vector at base point.
        base_point: array-like, shape=[n_vertices, 3]
            Surface, as the 3D coordinates of the vertices of its triangulation.

        Returns
        -------
        inner_product : array-like, shape=[...]
            Inner-product.

        References
        ----------
        .. [HSKCB2022] "Elastic shape analysis of surfaces with second-order
            Sobolev metrics: a comprehensive numerical framework".
            arXiv:2204.04238 [cs.CV], 25 Sep 2022.
        """
        h = tangent_vec_a
        k = tangent_vec_b
        point_a = base_point + h
        point_b = base_point + k
        inner_prod = 0
        if self.a0 > 0 or self.a2 > 0:
            v_areas = self.space.vertex_areas(base_point)
            if self.a0 > 0:
                inner_prod += self.a0 * gs.sum(
                    v_areas * gs.einsum("...bi,...bi->...b", h, k), axis=-1
                )
            if self.a2 > 0:
                laplacian_at_base_point = self.space.laplacian(base_point)
                inner_prod += self.a2 * gs.sum(
                    gs.einsum(
                        "...bi,...bi->...b",
                        laplacian_at_base_point(h),
                        laplacian_at_base_point(k),
                    )
                    / v_areas,
                    axis=-1,
                )
        if self.a1 > 0 or self.b1 > 0 or self.c1 > 0 or self.b1 > 0:
            one_forms_base_point = self.space.surface_one_forms(base_point)
            surface_metrics = self.space._surface_metric_matrices_from_one_forms(
                one_forms_base_point
            )
            areas = gs.sqrt(gs.linalg.det(surface_metrics))
            normals_at_base_point = self.space.normals(base_point)
            if self.c1 > 0:
                dn1 = self.space.normals(point_a) - normals_at_base_point
                dn2 = self.space.normals(point_b) - normals_at_base_point
                inner_prod += self.c1 * gs.sum(
                    gs.einsum("...bi,...bi->...b", dn1, dn2) * areas, axis=-1
                )
            if self.d1 > 0 or self.b1 > 0 or self.a1 > 0:
                ginv = gs.linalg.inv(surface_metrics)
                one_forms_a = self.space.surface_one_forms(point_a)
                one_forms_b = self.space.surface_one_forms(point_b)
                if self.d1 > 0:
                    one_forms_base_point_t = gs.transpose(
                        one_forms_base_point, (0, 2, 1)
                    )

                    one_forms_a_t = gs.transpose(one_forms_a, (0, 1, 3, 2))
                    xi1 = one_forms_a_t - one_forms_base_point_t

                    xi1_0 = gs.matmul(
                        gs.matmul(one_forms_base_point_t, ginv),
                        gs.matmul(
                            gs.transpose(xi1, (0, 1, 3, 2)), one_forms_base_point_t
                        )
                        - gs.matmul(one_forms_base_point, xi1),
                    )

                    one_forms_b_t = gs.transpose(one_forms_b, (0, 1, 3, 2))
                    xi2 = one_forms_b_t - one_forms_base_point_t
                    xi2_0 = gs.matmul(
                        gs.matmul(one_forms_base_point_t, ginv),
                        gs.matmul(
                            gs.transpose(xi2, (0, 1, 3, 2)), one_forms_base_point_t
                        )
                        - gs.matmul(one_forms_base_point, xi2),
                    )

                    inner_prod += self.d1 * gs.sum(
                        gs.einsum(
                            "...bii->...b",
                            gs.matmul(
                                xi1_0,
                                gs.matmul(ginv, gs.transpose(xi2_0, axes=(0, 1, 3, 2))),
                            ),
                        )
                        * areas
                    )
                if self.b1 > 0 or self.a1 > 0:
                    dg1 = (
                        gs.matmul(
                            one_forms_a, gs.transpose(one_forms_a, axes=(0, 1, 3, 2))
                        )
                        - surface_metrics
                    )
                    dg2 = (
                        gs.matmul(
                            one_forms_b, gs.transpose(one_forms_b, axes=(0, 1, 3, 2))
                        )
                        - surface_metrics
                    )
                    ginvdg1 = gs.matmul(ginv, dg1)
                    ginvdg2 = gs.matmul(ginv, dg2)
                    inner_prod += self.a1 * gs.sum(
                        gs.einsum("...bii->...b", gs.matmul(ginvdg1, ginvdg2)) * areas,
                        axis=-1,
                    )
                    inner_prod += self.b1 * gs.sum(
                        gs.einsum("...bii->...b", ginvdg1)
                        * gs.einsum("...bii->...b", ginvdg2)
                        * areas,
                        axis=-1,
                    )
        return inner_prod
