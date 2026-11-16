import io
import json
import re
from pathlib import Path

import numpy as np
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from app import llm

CARPETA_INDICE = Path("data/index")
CARPETA_DOCS = Path("data/docs")

# Páginas y manuales de Getnet que se van a usar como base de conocimiento.
# También es para hacer la ingesta inicial de datos en la memoria de los agentes.
URLS = [
    "https://www.getnet.net/en",
    "https://www.getnet.net/en/our-solutions/in-person-payments",
    "https://www.getnet.net/en/our-solutions/online-payments",
    "https://site.getnet.com.br/",
    "https://www.santander.com.br/blog/seus-negocios/link-de-pagamento/",
    "https://www.santander.com.br/blog/seus-negocios/antecipacao-de-recebiveis/",
    "https://site.getnet.com.br/wp-content/uploads/2025/09/Manul-GetSmart.pdf",
    "https://sitehml.getnet.com.br/wp-content/uploads/2024/01/Manul_GetClassica.pdf",
    "https://site.getnet.com.br/wp-content/uploads/2024/01/Manul_GetMini.pdf",
    "https://site.getnet.com.br/wp-content/uploads/2024/09/Folder_Credirio.pdf",
]


# 1) Descargar el texto de cada url (si es pdf se lee con pypdf, si es html con BeautifulSoup)
def descargar(url):
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    if url.lower().endswith(".pdf"):
        pdf = PdfReader(io.BytesIO(r.content))
        return "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()  # Se quita lo que no es contenido (menús, scripts, etc.)
    return soup.get_text("\n", strip=True)


# 2) Partir el texto en pedazos de 800 caracteres con 100 de traslape para no cortar ideas a la mitad (esto se le llama normalmente chuking, es una táctica común en videojuegos ya sea minnecraft, etcc)
def partir(texto, tamano=800, traslape=100):
    texto = re.sub(r"\s+", " ", texto).strip()
    pedazos = []
    for i in range(0, len(texto), tamano - traslape):
        pedazo = texto[i:i + tamano]
        if len(pedazo) > 100:  # Los chunks muy chiquitos no aportan nada
            pedazos.append(pedazo)
    return pedazos


# 3) Convertir textos a vectores (embeddings), se mandan de 100 en 100 a OpenAI
def embed(textos):
    vectores = []
    for i in range(0, len(textos), 100):
        resp = llm.get_client().embeddings.create(model=llm.EMBED_MODEL, input=textos[i:i + 100])
        vectores.extend(d.embedding for d in resp.data)
    v = np.array(vectores, dtype=np.float32)
    # Se normalizan para que el producto punto sea directamente la similitud coseno, el resultado de esta operacion matimática define qué tan similar son los mensajes
    return v / np.linalg.norm(v, axis=1, keepdims=True)


# 4) Construir el índice y guardarlo en almacinamiento  (chunks.json + vectors.npy)
def ingest():
    chunks = []
    for url in URLS:
        try:
            texto = descargar(url)
        except Exception as e:
            print("No se pudo descargar " + url + ": " + str(e))
            continue
        pedazos = partir(texto)
        for p in pedazos:
            chunks.append({"text": p, "url": url})
        print("OK " + url + ": " + str(len(pedazos)) + " pedazos")

    # Notas propias en markdown por si alguna página no se pudo descargar
    for archivo in CARPETA_DOCS.glob("*.md"):
        for p in partir(archivo.read_text(encoding="utf-8")):
            chunks.append({"text": p, "url": "local:" + archivo.name})

    if not chunks:
        raise SystemExit("No se pudo obtener ningún contenido")

    vectores = embed([c["text"] for c in chunks])
    CARPETA_INDICE.mkdir(parents=True, exist_ok=True)
    (CARPETA_INDICE / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    np.save(CARPETA_INDICE / "vectors.npy", vectores)
    print("Índice guardado con " + str(len(chunks)) + " pedazos")


# 5) Búsqueda: se compara la pregunta contra todos los pedazos y se regresan los k más parecidos
indice = None


def search(pregunta, k=4):
    global indice
    if indice is None:  # El índice se carga de disco solo la primera vez
        chunks = json.loads((CARPETA_INDICE / "chunks.json").read_text(encoding="utf-8"))
        indice = (chunks, np.load(CARPETA_INDICE / "vectors.npy"))

    chunks, vectores = indice
    puntajes = vectores @ embed([pregunta])[0]
    mejores = np.argsort(-puntajes)[:k]  # Índices ordenados de mayor a menor similitud
    return [{**chunks[i], "score": float(puntajes[i])} for i in mejores]


if __name__ == "__main__":
    ingest()
