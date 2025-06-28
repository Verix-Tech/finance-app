import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from matplotlib.transforms import Bbox
import re
from typing import Optional, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

def format_date_with_year(date_str: str) -> str:
    """
    Format date with year if not present
    """
    if '/' not in date_str:
        return date_str
    
    parts = date_str.split('/')
    if len(parts) == 2:
        # Add current year
        current_year = datetime.now().year
        return f"{parts[0]}/{parts[1]}/{current_year}"
    elif len(parts) == 3:
        return date_str
    
    return date_str

def format_date(date: str) -> str:
    return datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")

def preprocess_user_input(user_message: str) -> str:
    """
    Preprocess user input to improve accuracy
    """
    # Normalize whitespace
    message = re.sub(r'\s+', ' ', user_message.strip())
    
    # Standardize common abbreviations
    replacements = {
        'r$': 'R$',
        'rs': 'R$',
        'reais': 'R$',
        'real': 'R$',
        'pix': 'Pix',
        'credito': 'crédito',
        'debito': 'débito',
        'cartao': 'cartão',
        'farmacia': 'farmácia',
        'medico': 'médico',
        'academia': 'academia',
        'treino': 'treino',
        'remedio': 'remédio',
        'consulta': 'consulta',
        'exame': 'exame',
        'mesada': 'mesada',
        'pagamento': 'pagamento',
        'renda': 'renda',
        'receita': 'receita',
        'cripto': 'cripto',
        'acoes': 'ações',
        'bitcoin': 'bitcoin',
        'veterinario': 'veterinário',
        'cachorro': 'cachorro',
        'gato': 'gato',
        'animal': 'animal',
        'fatura': 'fatura',
        'boleto': 'boleto',
        'internet': 'internet',
        'faculdade': 'faculdade',
        'escola': 'escola',
        'curso': 'curso',
        'livro': 'livro',
        'estudo': 'estudo',
        'piscina': 'piscina',
        'jogos': 'jogos',
        'steam': 'steam',
        'passeio': 'passeio',
        'cinema': 'cinema',
        'show': 'show',
        'festa': 'festa',
        'pizza': 'pizza',
        'hamburguer': 'hambúrguer',
        'restaurante': 'restaurante',
        'lanche': 'lanche',
        'café': 'café',
        'sorvete': 'sorvete',
        'jantar': 'jantar',
    }
    
    for old, new in replacements.items():
        if "$" in old:
            old = old.replace("$", r"\$")
            message = re.sub(rf'\b{old}\B', new, message, flags=re.IGNORECASE)
        else:
            message = re.sub(rf'\b{old}\b', new, message, flags=re.IGNORECASE)
    
    return message

def extract_monetary_value(text: str) -> Optional[float]:
    """
    Extract monetary value from text with high accuracy
    """
    # Multiple patterns to catch different formats
    patterns = [
        r'R?\$?\s*([0-9]+(?:[.,][0-9]+)?)',  # R$ 100,50 or 100.50
        r'([0-9]+(?:[.,][0-9]+)?)\s*reais?',  # 100 reais
        r'([0-9]+(?:[.,][0-9]+)?)\s*rs?',     # 100 rs
        r'mil\s+e\s+([0-9]+)',               # mil e 500
        r'mil\s+e\s+(\w+)',             # mil e quinhentos
        r'([0-9]+)\s+mil',                   # 5 mil
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value_str = match.group(1)
                # Handle comma as decimal separator
                value_str = value_str.replace(',', '.')
                return float(value_str)
            except ValueError:
                continue
    
    # Handle written numbers
    written_numbers = {
        'mil': 1000,
        'dois mil': 2000,
        'tres mil': 3000,
        'quatro mil': 4000,
        'cinco mil': 5000,
        'dez mil': 10000,
        'quinhentos': 500,
        'seiscentos': 600,
        'setecentos': 700,
        'oitocentos': 800,
        'novecentos': 900,
    }
    
    for written, value in written_numbers.items():
        if written in text.lower():
            return value
    
    return None

def extract_date_info(text: str) -> Optional[Dict[str, str]]:
    """
    Extract date information from text
    """
    today = datetime.now()
    
    # Relative dates
    if 'ontem' in text.lower():
        yesterday = today - timedelta(days=1)
        return {
            'start_date': yesterday.strftime('%d/%m'),
            'end_date': yesterday.strftime('%d/%m')
        }
    elif 'hoje' in text.lower():
        return {
            'start_date': today.strftime('%d/%m'),
            'end_date': today.strftime('%d/%m')
        }
    elif 'semana passada' in text.lower():
        week_ago = today - timedelta(days=7)
        return {
            'days_before': '7'
        }
    elif 'mes passado' in text.lower():
        # Calculate last month
        if today.month == 1:
            last_month = today.replace(year=today.year-1, month=12)
        else:
            last_month = today.replace(month=today.month-1)
        
        start_date = last_month.replace(day=1)
        if today.month == 1:
            end_date = today.replace(year=today.year-1, month=12, day=31)
        else:
            if today.month == 3:
                end_date = today.replace(month=2, day=28 if today.year % 4 != 0 else 29)
            elif today.month in [5, 7, 10, 12]:
                end_date = today.replace(month=today.month-1, day=30)
            else:
                end_date = today.replace(month=today.month-1, day=31)
        
        return {
            'start_date': start_date.strftime('%d/%m'),
            'end_date': end_date.strftime('%d/%m')
        }
    
    # Specific date patterns
    date_patterns = [
        r'(\d{1,2})/(\d{1,2})',  # DD/MM
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        if len(matches) >= 2:
            try:
                start_match = matches[0]
                end_match = matches[1]
                
                if len(start_match) == 2:  # DD/MM
                    start_date = f"{start_match[0]}/{start_match[1]}"
                    end_date = f"{end_match[0]}/{end_match[1]}"
                else:  # DD/MM/YYYY
                    start_date = f"{start_match[0]}/{start_match[1]}/{start_match[2]}"
                    end_date = f"{end_match[0]}/{end_match[1]}/{end_match[2]}"
                
                return {
                    'start_date': start_date,
                    'end_date': end_date
                }
            except (ValueError, IndexError):
                continue
    
    return None

def categorize_transaction(description: str) -> str:
    """
    Categorize transaction based on description
    """
    description_lower = description.lower()
    
    # Food
    food_keywords = ['pizza', 'hambúrguer', 'restaurante', 'lanche', 'café', 'sorvete', 'jantar', 'almoço', 'ifood', 'uber eats', 'rappi']
    if any(keyword in description_lower for keyword in food_keywords):
        return "1"
    
    # Health
    health_keywords = ['farmácia', 'hospital', 'médico', 'academia', 'treino', 'remédio', 'consulta', 'exame']
    if any(keyword in description_lower for keyword in health_keywords):
        return "2"
    
    # Income
    income_keywords = ['salário', 'mesada', 'pagamento', 'renda', 'receita']
    if any(keyword in description_lower for keyword in income_keywords):
        return "3"
    
    # Investments
    investment_keywords = ['cripto', 'ações', 'bitcoin', 'investimento', 'renda fixa', 'renda variável']
    if any(keyword in description_lower for keyword in investment_keywords):
        return "4"
    
    # Pet
    pet_keywords = ['ração', 'veterinário', 'pet shop', 'cachorro', 'gato', 'animal']
    if any(keyword in description_lower for keyword in pet_keywords):
        return "5"
    
    # Bills
    bill_keywords = ['conta', 'fatura', 'boleto', 'internet', 'luz', 'água', 'parcela']
    if any(keyword in description_lower for keyword in bill_keywords):
        return "6"
    
    # Education
    education_keywords = ['faculdade', 'escola', 'curso', 'livro', 'estudo', 'material escolar']
    if any(keyword in description_lower for keyword in education_keywords):
        return "7"
    
    # Entertainment
    entertainment_keywords = ['piscina', 'jogos', 'steam', 'passeio', 'cinema', 'show', 'festa', 'netflix', 'spotify', 'uber']
    if any(keyword in description_lower for keyword in entertainment_keywords):
        return "8"
    
    return "0"  # Others

def extract_payment_method(text: str) -> str:
    """
    Extract payment method from text
    """
    text_lower = text.lower()
    
    if 'pix' in text_lower or 'transferência' in text_lower:
        return "1"
    elif 'crédito' in text_lower or 'cartão de crédito' in text_lower:
        return "2"
    elif 'débito' in text_lower or 'cartão de débito' in text_lower:
        return "3"
    elif 'dinheiro' in text_lower or 'cash' in text_lower or 'papel' in text_lower:
        return "4"
    
    return "0"  # Not informed

def validate_transaction_data(params: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate transaction data before processing
    """
    if not params.get('transaction_revenue'):
        return False, "Valor da transação não encontrado"
    
    try:
        value = float(params['transaction_revenue'])
        if value <= 0:
            return False, "Valor da transação deve ser maior que zero"
    except (ValueError, TypeError):
        return False, "Valor da transação inválido"
    
    if not params.get('transaction_type'):
        return False, "Tipo da transação não especificado"
    
    if params['transaction_type'] not in ['Despesa', 'Entrada']:
        return False, "Tipo da transação deve ser 'Despesa' ou 'Entrada'"
    
    return True, "OK"

def format_report(csv: str, aggr: bool = False) -> pd.DataFrame:
    csv_buffer = io.StringIO(csv)
    csv_buffer.seek(0)

    columns = ["ID", "Data", "Descricao", "Valor", "Categoria", "Tipo"] if not aggr else ["Data", "Valor"]
    
    report = pd.read_csv(csv_buffer)
    report = report[["transaction_id", "transaction_timestamp", "payment_description", "transaction_revenue", "payment_category_id", "transaction_type"]] if not aggr else report[["transaction_timestamp", "transaction_revenue"]]

    report.columns = columns
    
    report["Data"] = report["Data"].apply(lambda x: format_date(x))
    report["Valor"] = report["Valor"].apply(lambda x: f"R$ {x:,.2f}")

    return report
    
def create_table_image(df: pd.DataFrame, figsize: tuple = (12, 8), 
                      title: str = "Data Table", dpi: int = 300) -> bytes:
    """
    Create a table image from a pandas DataFrame.
    
    Args:
        df: pandas DataFrame to visualize
        figsize: figure size as (width, height)
        title: title for the table
        dpi: resolution of the output image
    
    Returns:
        bytes: image data as bytes
    """
    # Set style for better looking tables
    plt.style.use('seaborn-v0_8')
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis('tight')
    ax.axis('off')
    
    # Convert dataframe to proper format for table
    cell_text = df.values.tolist()
    col_labels = df.columns.tolist()
    
    # Create table
    table = ax.table(cellText=cell_text, 
                    colLabels=col_labels,
                    cellLoc='center',
                    loc='center',
                    bbox=Bbox.from_bounds(0, 0, 1, 1))
    
    # Style the table
    table.auto_set_font_size(True)
    # table.set_fontsize(9)
    table.scale(1.1, 4)
    
    # Style header row
    for i in range(len(df.columns)):
        table[(0, i)].set_facecolor('#18baf2')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Style alternating rows for better readability
    for i in range(1, len(df) + 1):
        for j in range(len(df.columns)):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#e7e7e7')
            else:
                table[(i, j)].set_facecolor('white')
    
    # Add title
    plt.title(title, fontsize=13, fontweight='bold', pad=20)
    
    # Save the image to bytes buffer
    import io
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    
    # Get the image data as bytes
    buffer.seek(0)
    image_bytes = buffer.getvalue()
    buffer.close()
    
    return image_bytes

def get_limit_percentage(limit_value: float) -> float:
    limit_90 = limit_value - ((90 / limit_value) * 100)
    return limit_90
