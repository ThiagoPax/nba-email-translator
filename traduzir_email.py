import os, imaplib, email, smtplib
from email.message import EmailMessage
from docx import Document
import requests
from dotenv import load_dotenv

# carrega variáveis de ambiente
load_dotenv()

IMAP_HOST  = os.getenv("IMAP_HOST")
SMTP_HOST  = os.getenv("SMTP_HOST")
USER       = os.getenv("MAIL_USER")
PWD        = os.getenv("MAIL_PASS")
DEST       = os.getenv("DESTINO")
OPENAI_KEY = os.getenv("OPENAI_KEY")

def pegar_ultimo_email():
    M = imaplib.IMAP4_SSL(IMAP_HOST)
    M.login(USER, PWD)
    M.select("INBOX")
    typ, data = M.search(None, '(UNSEEN)')
    if not data[0]:
        return None
    num = data[0].split()[-1]
    typ, raw = M.fetch(num, '(RFC822)')
    return email.message_from_bytes(raw[0][1])

def extrair_docx(msg):
    for part in msg.walk():
        fn = part.get_filename() or ""
        if fn.lower().endswith(".docx"):
            blob = part.get_payload(decode=True)
            with open("anexo.docx","wb") as f:
                f.write(blob)
            doc = Document("anexo.docx")
            return "\n".join(p.text for p in doc.paragraphs)
    return ""

def traduzir(texto):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }
    body = {
      "model":"gpt-4o-mini",
      "messages":[
        {"role":"system","content":"Você é tradutor profissional de basquete. Use termos da NBA."},
        {"role":"user"  ,"content": texto}
      ]
    }
    r = requests.post(url, json=body, headers=headers)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def reenviar(msg, traduzido):
    fwd = EmailMessage()
    fwd["Subject"] = "FW: " + msg["Subject"] + " – TRADUZIDO"
    fwd["From"]    = USER
    fwd["To"]      = DEST
    fwd.set_content(traduzido)
    # anexa PDF e DOCX originais
    for part in msg.walk():
        fn = part.get_filename()
        if fn:
            fwd.add_attachment(
                part.get_payload(decode=True),
                maintype=part.get_content_maintype(),
                subtype=part.get_content_subtype(),
                filename=fn)
    with smtplib.SMTP(SMTP_HOST, 587) as S:
        S.starttls()
        S.login(USER, PWD)
        S.send_message(fwd)

def main():
    msg = pegar_ultimo_email()
    if not msg: return
    texto = extrair_docx(msg)
    if not texto: return
    trad = traduzir(texto)
    reenviar(msg, trad)

if __name__=="__main__":
    main()
