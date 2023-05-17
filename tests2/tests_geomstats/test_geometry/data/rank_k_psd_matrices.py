from .base import _ProjectionMixinsTestData
from .fiber_bundle import FiberBundleTestData
from .manifold import ManifoldTestData
from .quotient_metric import QuotientMetricTestData


class RankKPSDMatricesTestData(_ProjectionMixinsTestData, ManifoldTestData):
    tolerances = {
        "to_tangent_is_tangent": {"atol": 1e-1},
    }
    xfails = ("to_tangent_is_tangent",)


class BuresWassersteinBundleTestData(FiberBundleTestData):
    fail_for_not_implemented_errors = False
    skips = (
        "horizontal_lift_vec",
        "horizontal_lift_is_horizontal",
    )

    xfails = ("tangent_riemannian_submersion_after_horizontal_lift",)


class PSDBuresWassersteinMetricTestData(QuotientMetricTestData):
    fail_for_autodiff_exceptions = False
    fail_for_not_implemented_errors = False

    xfails = ("log_after_exp",)
