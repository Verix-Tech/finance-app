import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from matplotlib.transforms import Bbox


def format_date_with_year(date: str) -> str:
    return date + "/" + datetime.now().strftime("%Y") \
        if len(date) == 5 \
        else date

def format_date(date: str) -> str:
    return datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")


def format_report(csv: str, aggr: bool = False) -> pd.DataFrame:
    csv_buffer = io.StringIO(csv)
    csv_buffer.seek(0)

    columns = ["Data", "Descricao", "Valor", "Categoria", "Tipo"] if not aggr else ["Data", "Valor"]
    
    report = pd.read_csv(csv_buffer)
    report = report[["transaction_timestamp", "payment_description", "transaction_revenue", "payment_category", "transaction_type"]] if not aggr else report[["transaction_timestamp", "transaction_revenue"]]

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
