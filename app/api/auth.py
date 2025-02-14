# from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
# from sqlalchemy.orm import Session
# from datetime import datetime, timedelta
# from jose import JWTError, jwt
# from passlib.context import CryptContext
# from app.database import get_db
# from app.models import User
# from app.schemas import UserCreate, Token
#
# router = APIRouter()
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
#
# # Secret key - in production, use a secure environment variable
# SECRET_KEY = "your-secret-key-here"  # Change this in production!
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30
#
#
# def create_access_token(data: dict):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt
#
#
# @router.post("/register", response_model=Token)
# async def register_user(user: UserCreate, db: Session = Depends(get_db)):
#     # Check if user exists
#     db_user = db.query(User).filter(User.username == user.username).first()
#     if db_user:
#         raise HTTPException(
#             status_code=400,
#             detail="Username already registered"
#         )
#
#     # Create new user
#     hashed_password = pwd_context.hash(user.password)
#     db_user = User(username=user.username, hashed_password=hashed_password)
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#
#     # Create access token
#     access_token = create_access_token(data={"sub": user.username})
#     return {"access_token": access_token, "token_type": "bearer"}
#
#
# @router.post("/token", response_model=Token)
# async def login(
#         form_data: OAuth2PasswordRequestForm = Depends(),
#         db: Session = Depends(get_db)
# ):
#     # Check username
#     user = db.query(User).filter(User.username == form_data.username).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#
#     # Check password
#     if not pwd_context.verify(form_data.password, user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#
#     # Create access token
#     access_token = create_access_token(data={"sub": user.username})
#     return {"access_token": access_token, "token_type": "bearer"}
#
#
# async def get_current_user(
#         token: str = Depends(oauth2_scheme),
#         db: Session = Depends(get_db)
# ):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#     except JWTError:
#         raise credentials_exception
#
#     user = db.query(User).filter(User.username == username).first()
#     if user is None:
#         raise credentials_exception
#     return user