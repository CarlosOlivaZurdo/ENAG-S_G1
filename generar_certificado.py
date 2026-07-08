"""Genera un certificado TLS **autofirmado** (cert.pem + key.pem) para servir la app por
HTTPS en local. Solo lo crea si no existe.

Uso (lo llama iniciar_chatbot.bat automáticamente):

    python generar_certificado.py

Aviso: es un certificado autofirmado (no emitido por una autoridad). La primera vez, el
navegador mostrará «La conexión no es privada»; hay que pulsar «Avanzado → Continuar».
No es para producción: para un despliegue real se usa un certificado emitido (Let's
Encrypt) o un proxy inverso. Los ficheros cert.pem/key.pem NO se versionan (ver .gitignore).
"""
import datetime
import ipaddress
import os

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

AQUI = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.join(AQUI, "cert.pem")
KEY = os.path.join(AQUI, "key.pem")


def generar() -> bool:
    """Crea cert.pem + key.pem si no existen. Devuelve True si los ha creado."""
    if os.path.exists(CERT) and os.path.exists(KEY):
        return False

    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Comparador Calidad Gas (autofirmado)"),
    ])
    # Válido para localhost y 127.0.0.1 (acceso en este equipo). El acceso por IP de red
    # seguirá mostrando aviso porque el certificado no cubre esa IP concreta.
    san = x509.SubjectAlternativeName([
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ])
    ahora = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - datetime.timedelta(days=1))
        .not_valid_after(ahora + datetime.timedelta(days=3650))  # 10 años
        .add_extension(san, critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(clave, hashes.SHA256())
    )
    with open(KEY, "wb") as f:
        f.write(clave.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    with open(CERT, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    return True


if __name__ == "__main__":
    creado = generar()
    print("  Certificado autofirmado creado (cert.pem + key.pem)." if creado
          else "  Certificado ya existente; se reutiliza.")
