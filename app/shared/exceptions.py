from fastapi import HTTPException, status


def not_found(entidad: str):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entidad} no encontrado"
    )


def forbidden():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tiene permisos para realizar esta acción"
    )


def bad_request(mensaje: str):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=mensaje
    )


def conflict(mensaje: str):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=mensaje
    )
