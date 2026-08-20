import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
imports = '''from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt'''
content = content.replace('from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks', imports)

# Add security config
security_config = '''
# ==========================================
# GÜVENLİK VE JWT YAPILANDIRMASI
# ==========================================
SECRET_KEY = "depo_stok_super_gizli_anahtari"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict):
    to_encode = data.copy()
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Yetkisiz erişim")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Yetkisiz erişim - Token Geçersiz")

'''
content = content.replace('app = FastAPI(title="Akıllı Depo API")', 'app = FastAPI(title="Akıllı Depo API")\n' + security_config)

# Update Login endpoint
login_old = '''@app.post("/login")
def login(payload: LoginPayload):
    if payload.username == "admin" and payload.password == "12345":
        return {"status": "success", "token": "admin-token-123", "role": "admin"}
    elif payload.username == "gorevli" and payload.password == "12345":
        return {"status": "success", "token": "worker-token-456", "role": "worker"}
    raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya şifre")'''

login_new = '''@app.post("/login")
def login(payload: LoginPayload):
    if payload.username == "admin" and payload.password == "12345":
        token = create_access_token({"sub": payload.username, "role": "admin"})
        return {"status": "success", "token": token, "role": "admin"}
    elif payload.username == "gorevli" and payload.password == "12345":
        token = create_access_token({"sub": payload.username, "role": "worker"})
        return {"status": "success", "token": token, "role": "worker"}
    raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya şifre")'''
content = content.replace(login_old, login_new)

# Protect specific endpoints
content = content.replace('def update_stock_manual(payload: UpdateStockPayload, db: Session = Depends(get_db)):', 'def update_stock_manual(payload: UpdateStockPayload, db: Session = Depends(get_db), user: str = Depends(get_current_user)):')
content = content.replace('def waste_batch(batch_id: int, db: Session = Depends(get_db)):', 'def waste_batch(batch_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):')
content = content.replace('def update_batch_skt(batch_id: int, payload: UpdateSktPayload, db: Session = Depends(get_db)):', 'def update_batch_skt(batch_id: int, payload: UpdateSktPayload, db: Session = Depends(get_db), user: str = Depends(get_current_user)):')

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Backend JWT security applied.')
