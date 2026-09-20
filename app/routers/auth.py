from fastapi import APIRouter, HTTPException, Request, Response, status

from app.routers.dependencies import Authentication
from app.schemas import KitchenUserResponse, LoginRequest, ReceptionUserResponse


router = APIRouter(prefix="/auth", tags=["authentication"])


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
