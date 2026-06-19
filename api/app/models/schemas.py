from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    login: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: str
    nome: str
    role: str = "operador"
    mobile_admin: int = 0


class UsuarioMobile(BaseModel):
    idusuario: int
    login: str
    nomecompleto: Optional[str] = None
    idgrupo: Optional[int] = None
    inativo: Optional[int] = None
    tem_mobile: int = 0
    mobile_admin: int = 0


class SenhaMobileRequest(BaseModel):
    senha: Optional[str] = None


class DepositoResponse(BaseModel):
    cddeposito: int
    deposito: str


class ProdutoResponse(BaseModel):
    cdproduto: int
    produto: str
    codigobarra: Optional[str] = None
    qtdeatual: Optional[float] = None


class BipagemRequest(BaseModel):
    cdproduto: int
    cddeposito: int
    qtde: float
    operador: Optional[str] = None
    device_id: Optional[str] = None


class BipagemResponse(BaseModel):
    cdproduto: int
    cddeposito: int
    qtde: float
    nova_qtde: float
    mensagem: str
    alerta: Optional[str] = None


class EditarBipagemRequest(BaseModel):
    qtde: float
    cddeposito: int
    motivo: Optional[str] = None
    device_id: Optional[str] = None


class ItemRelatorio(BaseModel):
    cdproduto: int
    produto: str
    codigobarra: Optional[str] = None
    qtde_sistema: Optional[float] = None
    qtde_contada: Optional[float] = None
    diferenca: Optional[float] = None
    operador: Optional[str] = None


class ConsolidarRequest(BaseModel):
    cddeposito: int
    operador: Optional[str] = None
    supervisor_login: Optional[str] = None
    supervisor_senha: Optional[str] = None
    recontagem_confirmada: bool = False
    idempresa: int = 1


class ItemHistorico(BaseModel):
    cdproduto: int
    produto: str
    cddeposito: int
    deposito: str
    qtde_contada: Optional[float] = None
    qtde_sistema: Optional[float] = None
    data: Optional[datetime] = None
    operador: Optional[str] = None


class ResumoContagem(BaseModel):
    total_deposito: int
    contados: int
    nao_contados: int
    produtos_nao_contados: list[str] = []


class OperadorRequest(BaseModel):
    nome: str


class OperadorResponse(BaseModel):
    id: int
    nome: str
    ativo: int


class LogItem(BaseModel):
    id: int
    tipo: str
    cddeposito: Optional[int] = None
    cdproduto: Optional[int] = None
    produto: Optional[str] = None
    operador: Optional[str] = None
    login_usuario: Optional[str] = None
    qtde_antes: Optional[float] = None
    qtde_depois: Optional[float] = None
    motivo: Optional[str] = None
    device_id: Optional[str] = None
    data_hora: Optional[datetime] = None
