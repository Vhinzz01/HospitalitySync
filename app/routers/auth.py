from fastapi import APIRouter, HTTPException, Request, Response, status

from app.routers.dependencies import Authentication, DemoAccessOperations
from app.schemas import KitchenUserResponse, LoginRequest, ReceptionUserResponse
from app.services import DemoAccessError


router = APIRouter(prefix="/auth", tags=["authentication"])
DEVICE_COOKIE = "hospitalitysync_device"


@router.post("/login", response_model=ReceptionUserResponse)
def login(
    credentials: LoginRequest,
    request: Request,
    authentication: Authentication,
) -> ReceptionUserResponse:
    user = authentication.authenticate_receptionist(
        email=credentials.email,
        password=credentials.password.get_secret_value(),
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is invalid.",
        )

    request.session.clear()
    request.session["user_id"] = user.id
    return ReceptionUserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/kitchen/login", response_model=KitchenUserResponse)
def kitchen_login(
    credentials: LoginRequest,
    request: Request,
    authentication: Authentication,
) -> KitchenUserResponse:
    user = authentication.authenticate_kitchen_user(
        email=credentials.email,
        password=credentials.password.get_secret_value(),
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is invalid.",
        )
    request.session.clear()
    request.session["user_id"] = user.id
    return KitchenUserResponse.model_validate(user)


@router.post("/demo/{area}", include_in_schema=False)
def demo_access(
    area: str,
    request: Request,
    response: Response,
    service: DemoAccessOperations,
) -> dict[str, str]:
    if not request.app.state.settings.enable_demo_access:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    try:
        access = service.enter(area)
    except DemoAccessError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    request.session.clear()
    if access.user_id is not None:
        request.session["user_id"] = access.user_id
    if access.device_credential is not None:
        settings = request.app.state.settings
        response.set_cookie(
            DEVICE_COOKIE,
            access.device_credential,
            max_age=settings.device_cookie_max_age_seconds,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="strict",
            path="/guest",
        )
    return {"destination": access.destination}
