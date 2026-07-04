from fastapi import APIRouter

from .health import router as health_router
from .login import router as login_router
from .logout import router as logout_router
from .security_agents import router as security_agents_router
from .tiers import router as tiers_router
from .users import router as users_router

router = APIRouter(prefix="/v1")
router.include_router(health_router)
router.include_router(login_router)
router.include_router(logout_router)
router.include_router(users_router)
router.include_router(security_agents_router)
router.include_router(tiers_router)
