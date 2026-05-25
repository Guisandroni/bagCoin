"""Statement parser agent — detects and parses bank statement formats.

Supports Nubank CSV, generic Brazilian CSV, OFX, and PDF text extraction.
Pure logic — no database access needed.
"""

import base64
import csv
import io
import logging
import re
from datetime import datetime
from typing import Any

from app.services.docx_text import extract_docx_text

logger = logging.getLogger(__name__)

# Categorização heurística baseada em palavras-chave do extrato
CATEGORY_MAP = {
    "uber": "Transporte",
    "99": "Transporte",
    "taxi": "Transporte",
    "combustivel": "Transporte",
    "gasolina": "Transporte",
    "posto": "Transporte",
    "estacionamento": "Transporte",
    "mercado": "Alimentação",
    "supermercado": "Alimentação",
    "sup": "Alimentação",
    "padaria": "Alimentação",
    "restaurante": "Alimentação",
    "lanche": "Alimentação",
    "ifood": "Alimentação",
    "rappi": "Alimentação",
    "uber eats": "Alimentação",
    "farmacia": "Saúde",
    "droga": "Saúde",
    "remedio": "Saúde",
    "consulta": "Saúde",
    "medico": "Saúde",
    "plano de saude": "Saúde",
    "netflix": "Entretenimento",
    "spotify": "Entretenimento",
    "prime video": "Entretenimento",
    "disney": "Entretenimento",
    "cinema": "Entretenimento",
    "jogo": "Entretenimento",
    "steam": "Entretenimento",
    "luz": "Moradia",
    "energia": "Moradia",
    "eletrica": "Moradia",
    "agua": "Moradia",
    "sabesp": "Moradia",
    "gas": "Moradia",
    "internet": "Moradia",
    "telefone": "Moradia",
    "aluguel": "Moradia",
    "condominio": "Moradia",
    "escola": "Educação",
    "curso": "Educação",
    "faculdade": "Educação",
    "universidade": "Educação",
    "udemy": "Educação",
    "coursera": "Educação",
    "seguro": "Seguros",
    "pix": "Transferência",
    "transferencia": "Transferência",
    "ted": "Transferência",
    "doc": "Transferência",
    "saque": "Saque",
    "rendimento": "Investimentos",
    "rdb": "Investimentos",
    "aplicacao": "Investimentos",
    "salario": "Renda",
    "pagamento": "Renda",
    "recebido": "Renda",
    "inss": "Renda",
}


def _guess_category(description: str) -> str:
    """Tenta inferir a categoria a partir da descrição da transação."""
    desc_lower = description.lower()
    for keyword, category in CATEGORY_MAP.items():
        if keyword in desc_lower:
            return category
    return "Outros"


def _parse_brazilian_date(date_str: str) -> str | None:
    """Converte datas brasileiras (DD/MM/YYYY) para ISO (YYYY-MM-DD)."""
    try:
        dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        try:
            dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None


def _parse_brazilian_value(value_str: str) -> float | None:
    """Converte valores brasileiros (1.234,56 ou 1234,56) para float."""
    if not value_str or not value_str.strip():
        return None
    try:
        # Remove espaços e troca separadores
        val = value_str.strip().replace(" ", "")
        # Se tem ponto e vírgula: 1.234,56 -> remove ponto, troca vírgula
        if "," in val:
            val = val.replace(".", "").replace(",", ".")
        return float(val)
    except ValueError:
        return None


def _normalize_text(text: str) -> str:
    return (
        text.lower()
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def _is_identifier_like(value: str) -> bool:
    """Return True for CNPJ/CPF/CEP/phone/IDs, not transaction amounts."""
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 8:
        return True
    if re.fullmatch(r"\d{1,3}(?:\.\d{3}){2,},\d{2}", value.strip()):
        parsed = _parse_brazilian_value(value)
        return parsed is not None and parsed >= 100_000
    return False


def _looks_like_date_token(value: str) -> bool:
    stripped = value.strip()
    return bool(
        re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", stripped)
        or re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", stripped)
        or re.fullmatch(r"(?:19|20)\d{2}", stripped)
    )


def _extract_money_candidate(line: str) -> tuple[str, tuple[int, int]] | None:
    """Extract the most likely money value from a loose statement/receipt line."""
    if _looks_like_date_token(line):
        return None
    money_patterns = [
        r"R\$\s*(-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+[,.]\d{2})",
        r"(-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+[,.]\d{2}|-?\d{1,5})\s*(?:reais|brl)\b",
        r"(-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+[,.]\d{2})(?![\d.,])",
        r"\b(-?\d{1,5})\b\s*$",
    ]
    candidates: list[tuple[str, tuple[int, int]]] = []
    for pattern in money_patterns:
        for match in re.finditer(pattern, line, flags=re.IGNORECASE):
            value = match.group(1)
            if _is_identifier_like(value) or _looks_like_date_token(value):
                continue
            candidates.append((value, match.span(1)))
        if candidates:
            break
    if not candidates:
        return None
    return candidates[-1]


def _clean_transaction_description(line: str, span: tuple[int, int]) -> str:
    before = line[: span[0]]
    after = line[span[1] :]
    description = f"{before} {after}"
    description = re.sub(r"R\$", " ", description, flags=re.IGNORECASE)
    description = re.sub(r"\b(?:cnpj|cpf|cep)\b[:\s.-]*\d[\d./ -]+", " ", description, flags=re.IGNORECASE)
    description = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", " ", description)
    description = re.sub(r"\d{3}\.\d{3}\.\d{3}-\d{2}", " ", description)
    description = re.sub(r"\b\d{5}-?\d{3}\b", " ", description)
    description = re.sub(r"\s+", " ", description).strip(" -:;|")
    return description or "Transação bancária"


def _is_statement_csv(content: str) -> bool:
    """Heurística para detectar se um CSV é extrato bancário."""
    content_lower = content.lower()
    keywords = ["data", "valor", "descrição", "saldo", "débito", "crédito", "histórico", "extrato"]
    return sum(1 for k in keywords if k in content_lower) >= 3


def _is_statement_ofx(content: str) -> bool:
    """Heurística para detectar OFX."""
    return "<ofx>" in content.lower() or "<stmttrn>" in content.lower()


def _is_statement_text(content: str) -> bool:
    """Heurística para detectar extrato em texto puro (após extração de PDF)."""
    lines = content.strip().split("\n")
    date_patterns = 0
    value_patterns = 0
    for line in lines[:30]:
        if re.search(r"\d{2}/\d{2}/\d{4}", line):
            date_patterns += 1
        if re.search(r"[\d\.,]+\s*(?:R\$|BRL)?", line):
            value_patterns += 1
    return date_patterns >= 5 and value_patterns >= 5


def parse_nubank_csv(content: str) -> list[dict[str, Any]]:
    """Parse de CSV do Nubank: Data,Valor,Identificador,Descrição."""
    transactions = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        try:
            date_str = row.get("Data", "").strip()
            value_str = row.get("Valor", "").strip()
            desc = row.get("Descrição", "").strip()
            if not date_str or not value_str:
                continue
            date = _parse_brazilian_date(date_str)
            amount = _parse_brazilian_value(value_str)
            if date is None or amount is None:
                continue
            tx_type = "INCOME" if amount > 0 else "EXPENSE"
            transactions.append(
                {
                    "date": date,
                    "amount": abs(amount),
                    "type": tx_type,
                    "description": desc,
                    "category": _guess_category(desc),
                    "raw": f"{date_str} | {value_str} | {desc}",
                }
            )
        except Exception as e:
            logger.warning(f"Erro ao parsear linha Nubank: {e}")
            continue
    return transactions


def _preprocess_csv(content: str) -> str:
    """Limpa CSVs malformados (ex: linha de título antes do header)."""
    lines = content.strip().split("\n")
    if not lines:
        return content
    # Se a primeira linha não parece um header válido (não contém 'Data'),
    # remove-a e usa a próxima como header
    first_line_lower = lines[0].lower()
    if "data" not in first_line_lower and len(lines) > 1:
        # Verifica se a segunda linha é um header válido
        second_line_lower = lines[1].lower()
        if "data" in second_line_lower:
            lines = lines[1:]
    return "\n".join(lines)


def parse_generic_csv(content: str) -> list[dict[str, Any]]:
    """Parse de CSV genérico de banco brasileiro.

    Tenta detectar colunas comuns: Data/Histórico/Docto./Crédito/Débito/Saldo
    """
    transactions = []
    content = _preprocess_csv(content)
    # Detecta delimitador
    first_lines = "\n".join(content.strip().split("\n")[:5])
    delimiter = ";" if ";" in first_lines else ","
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    for row in reader:
        try:
            # Tenta mapear colunas comuns (com variações de case e acentos)
            date_str = ""
            desc = ""
            credit = ""
            debit = ""
            for k, v in row.items():
                if not k:
                    continue
                k_lower = k.lower().strip()
                v_stripped = v.strip() if v else ""
                if "data" in k_lower and not date_str:
                    date_str = v_stripped
                elif (
                    any(x in k_lower for x in ["histórico", "historico", "descrição", "descricao"])
                    and not desc
                ):
                    desc = v_stripped
                elif any(x in k_lower for x in ["crédito", "credito", "entrada"]) and not credit:
                    credit = v_stripped
                elif (
                    any(x in k_lower for x in ["débito", "debito", "saída", "saida"]) and not debit
                ):
                    debit = v_stripped

            # Validações básicas
            if not date_str:
                continue
            date = _parse_brazilian_date(date_str)
            if date is None:
                continue
            # Evita linhas de metadados
            if not desc or any(
                x in desc.lower() for x in ["filtro", "resultados", "últimos", "ultimos"]
            ):
                continue
            # Deve ter pelo menos um valor em crédito ou débito
            if not (credit and credit.strip()) and not (debit and debit.strip()):
                continue

            amount = None
            tx_type = "EXPENSE"
            if credit and credit.strip():
                amount = _parse_brazilian_value(credit)
                if amount and amount > 0:
                    tx_type = "INCOME"
            if amount is None and debit and debit.strip():
                amount = _parse_brazilian_value(debit)
                if amount and amount > 0:
                    tx_type = "EXPENSE"
            if amount is None or amount <= 0:
                continue
            transactions.append(
                {
                    "date": date,
                    "amount": amount,
                    "type": tx_type,
                    "description": desc or "Transação bancária",
                    "category": _guess_category(desc),
                    "raw": f"{date_str} | {desc} | {credit or debit}",
                }
            )
        except Exception as e:
            logger.warning(f"Erro ao parsear linha genérica: {e}")
            continue
    return transactions


def parse_ofx(content: str) -> list[dict[str, Any]]:
    """Parse de OFX usando regex (evita dependência de bibliotecas pesadas).

    Extrai transações <STMTTRN>... </STMTTRN>
    """
    transactions = []

    def tag_value(block: str, tag: str) -> str | None:
        match = re.search(rf"<{tag}>\s*([^<\r\n]+)", block, re.IGNORECASE)
        return match.group(1).strip() if match else None

    # Encontra todos os blocos STMTTRN
    stmt_blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL | re.IGNORECASE)
    for block in stmt_blocks:
        try:
            trntype = tag_value(block, "TRNTYPE")
            date_str = tag_value(block, "DTPOSTED")
            amount_str = tag_value(block, "TRNAMT")
            memo = tag_value(block, "MEMO")
            fitid = tag_value(block, "FITID")
            if not date_str or not amount_str:
                continue
            date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
            amount = float(amount_str)
            desc = memo or fitid or "Transação OFX"
            trn_type = (trntype or "").upper()
            if trn_type == "CREDIT" or trn_type == "DEP":
                tx_type = "INCOME"
            elif trn_type in {"ATM", "DEBIT", "FEE", "PAYMENT", "POS"}:
                tx_type = "EXPENSE"
            elif trn_type == "XFER":
                tx_type = "EXPENSE" if amount < 0 else "INCOME"
            else:
                tx_type = "INCOME" if amount > 0 else "EXPENSE"
            transactions.append(
                {
                    "date": date,
                    "amount": abs(amount),
                    "type": tx_type,
                    "description": desc,
                    "category": _guess_category(desc),
                    "raw": f"{date} | {amount} | {desc}",
                }
            )
        except Exception as e:
            logger.warning(f"Erro ao parsear bloco OFX: {e}")
            continue
    return transactions


def _money_token_matches(text: str) -> list[re.Match[str]]:
    return list(re.finditer(r"-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+[,.]\d{2}", text))


def _looks_like_document_number(text: str) -> bool:
    return bool(re.fullmatch(r"\d{3,12}", text.strip()))


def _infer_statement_type(description: str, amount: float, balance_delta: float | None) -> str:
    if balance_delta is not None and abs(abs(balance_delta) - amount) <= 0.02:
        return "INCOME" if balance_delta > 0 else "EXPENSE"

    desc_norm = _normalize_text(description)
    income_tokens = (
        "credito",
        "credit",
        "recebido",
        "recebida",
        "salario",
        "deposito",
        "estorno",
        "devolucao",
        "rendimentos",
        "rendimento",
        "inss",
    )
    expense_tokens = (
        "debito",
        "debit",
        "deb aut",
        "pagamento",
        "pgto",
        "compra",
        "saque",
        "tarifa",
        "iof",
        "boleto",
        "darf",
        "tributo",
        "fatura",
    )
    if any(token in desc_norm for token in income_tokens):
        return "INCOME"
    if any(token in desc_norm for token in expense_tokens):
        return "EXPENSE"
    return "INCOME" if amount < 0 else "EXPENSE"


def _description_from_pdf_record(lines: list[str], amount_text: str) -> str:
    cleaned_lines: list[str] = []
    for line in lines:
        line = re.sub(re.escape(amount_text), " ", line)
        for match in _money_token_matches(line):
            line = line.replace(match.group(0), " ")
        line = re.sub(r"\b(?:docto\.?|documento)\b", " ", line, flags=re.IGNORECASE)
        line = re.sub(r"\s+", " ", line).strip(" -:;|")
        if (
            not line
            or _looks_like_document_number(line)
            or _looks_like_date_token(line)
            or _normalize_text(line)
            in {"data", "historico", "credito r$", "debito r$", "saldo r$", "total creditos", "total debitos"}
        ):
            continue
        cleaned_lines.append(line)

    if not cleaned_lines:
        return "Transação bancária"

    joined = " ".join(cleaned_lines)
    joined = re.sub(r"\b\d{3,12}\b", " ", joined)
    joined = re.sub(r"\s+", " ", joined).strip(" -:;|")
    return joined or cleaned_lines[0]


def _parse_pdf_record(
    date_str: str,
    lines: list[str],
    previous_balance: float | None,
) -> tuple[dict[str, Any] | None, float | None]:
    date = _parse_brazilian_date(date_str)
    if date is None:
        return None, previous_balance

    money_values: list[tuple[str, float]] = []
    for line in lines:
        for match in _money_token_matches(line):
            value_text = match.group(0)
            value = _parse_brazilian_value(value_text)
            if value is not None:
                money_values.append((value_text, value))

    if not money_values:
        return None, previous_balance

    amount_text, amount = money_values[-1]
    current_balance = previous_balance
    balance_delta = None
    if len(money_values) >= 2:
        amount_text, amount = money_values[-2]
        current_balance = money_values[-1][1]
        if previous_balance is not None:
            balance_delta = current_balance - previous_balance

    if amount == 0:
        return None, current_balance

    description = _description_from_pdf_record(lines, amount_text)
    tx_type = _infer_statement_type(description, abs(amount), balance_delta)
    return (
        {
            "date": date,
            "amount": abs(amount),
            "type": tx_type,
            "description": description,
            "category": _guess_category(description),
            "raw": " | ".join([date_str, *lines]),
        },
        current_balance,
    )


def _parse_pdf_vertical_statement(content: str) -> list[dict[str, Any]]:
    transactions: list[dict[str, Any]] = []
    current_date: str | None = None
    current_lines: list[str] = []
    previous_balance: float | None = None

    def flush() -> None:
        nonlocal current_date, current_lines, previous_balance
        if not current_date:
            return
        parsed, balance = _parse_pdf_record(current_date, current_lines, previous_balance)
        if parsed:
            transactions.append(parsed)
        previous_balance = balance
        current_date = None
        current_lines = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _normalize_text(line).startswith(("total creditos", "documento gerado")):
            flush()
            break
        match = re.match(r"^(\d{2}/\d{2}/\d{4})(?:\s+(.+))?$", line)
        if match:
            flush()
            current_date = match.group(1)
            current_lines = [match.group(2).strip()] if match.group(2) else []
            continue
        if current_date:
            current_lines.append(line)
    flush()
    return transactions


def parse_pdf_statement(content: str) -> list[dict[str, Any]]:
    """Tenta extrair transações de texto de PDF de extrato.

    Heurística: procura por linhas com data + valor + descrição.
    """
    vertical_transactions = _parse_pdf_vertical_statement(content)
    if vertical_transactions:
        return vertical_transactions

    transactions = []
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.search(r"(\d{2}/\d{2}/\d{4})\s+(.+)$", line)
        if match:
            try:
                date_str = match.group(1)
                rest = match.group(2).strip()
                date = _parse_brazilian_date(date_str)
                if date is None:
                    continue
                candidate = _extract_money_candidate(rest)
                if not candidate:
                    continue
                value_str, value_span = candidate
                amount = _parse_brazilian_value(value_str)
                if amount is None or amount == 0:
                    continue
                desc = _clean_transaction_description(rest, value_span)
                tx_type = "INCOME" if amount > 0 else "EXPENSE"
                transactions.append(
                    {
                        "date": date,
                        "amount": abs(amount),
                        "type": tx_type,
                        "description": desc,
                        "category": _guess_category(desc),
                        "raw": line,
                    }
                )
            except Exception as e:
                logger.warning(f"Erro ao parsear linha PDF: {e}")
                continue
    return transactions


def parse_statement(media: dict[str, Any]) -> list[dict[str, Any]]:
    """Detecta o formato do extrato e faz parse.

    Args:
        media: dict com 'mimetype' e 'data' (base64)

    Returns:
        Lista de transações extraídas
    """
    mimetype = media.get("mimetype", "")
    filename = (media.get("filename") or "").lower()
    data = media.get("data", "")
    if not data:
        return []

    content = ""
    try:
        decoded = base64.b64decode(data)
        if mimetype == "application/pdf":
            # Extrai texto do PDF
            try:
                import PyPDF2

                reader = PyPDF2.PdfReader(io.BytesIO(decoded))
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        content += page_text + "\n"
            except ImportError:
                logger.error("PyPDF2 não instalado")
                return []
        elif (
            "wordprocessingml.document" in mimetype
            or mimetype == "application/msword"
            or filename.endswith(".docx")
        ):
            content = extract_docx_text(decoded) or ""
        else:
            content = decoded.decode("utf-8", errors="replace")
    except Exception as e:
        logger.error(f"Erro ao decodificar mídia: {e}")
        return []

    if not content.strip():
        return []

    logger.info(f"Parseando extrato. Tipo: {mimetype}, tamanho: {len(content)} chars")

    # Detecta formato e faz parse
    transactions = []
    if _is_statement_ofx(content):
        transactions = parse_ofx(content)
        logger.info(f"OFX parseado: {len(transactions)} transações")
    elif mimetype == "application/pdf" or filename.endswith(".docx"):
        transactions = parse_pdf_statement(content)
        logger.info(f"Documento/texto parseado: {len(transactions)} transações")
    elif _is_statement_csv(content):
        # Tenta Nubank primeiro
        if "Identificador" in content and "Descrição" in content:
            transactions = parse_nubank_csv(content)
            logger.info(f"CSV Nubank parseado: {len(transactions)} transações")
        else:
            transactions = parse_generic_csv(content)
            logger.info(f"CSV genérico parseado: {len(transactions)} transações")
    elif _is_statement_text(content):
        transactions = parse_pdf_statement(content)
        logger.info(f"Documento/texto parseado: {len(transactions)} transações")
    else:
        logger.info("Conteúdo não reconhecido como extrato bancário")
        return []

    # Filtra duplicatas por raw
    seen = set()
    unique = []
    for tx in transactions:
        key = tx.get("raw", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(tx)
    return unique


def detect_statement(state: dict[str, Any]) -> bool:
    """Detecta se o estado atual contém um extrato bancário.

    Primeiro faz checagem rápida (mimetype + filename), sem parse completo.
    Se falhar, faz parse completo como fallback.
    """
    source_format = state.get("source_format", "text")
    if source_format not in ["document", "text"]:
        return False
    media = state.get("context", {}).get("media")
    if not media:
        return False

    # Checagem rápida por mimetype / filename
    mimetype = media.get("mimetype", "")
    filename = (media.get("filename") or "").lower()
    if mimetype in ("text/csv", "application/csv", "text/plain", "application/ofx", "text/ofx"):
        return True
    if filename.endswith((".csv", ".ofx", ".qfx")):
        return True
    if filename.endswith(".docx"):
        keywords_in_name = [
            "extrato",
            "fatura",
            "movimento",
            "conta",
            "banco",
            "nubank",
            "itau",
            "bradesco",
            "caixa",
            "santander",
        ]
        if any(k in filename for k in keywords_in_name):
            return True
    if filename.endswith(".pdf"):
        keywords_in_name = [
            "extrato",
            "fatura",
            "movimento",
            "conta",
            "banco",
            "nubank",
            "itau",
            "bradesco",
            "caixa",
            "santander",
        ]
        if any(k in filename for k in keywords_in_name):
            return True

    # Fallback: parse completo (para detecção de conteúdo)
    transactions = parse_statement(media)
    return len(transactions) >= 3
