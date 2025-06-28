import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
import subprocess

def find_python_files(directory):
    """Encontra todos os arquivos Python no diretório e subdiretórios."""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    return python_files

def format_with_black(file_path):
    """Formata um arquivo usando o Black."""
    try:
        subprocess.run(["black", str(file_path)], check=True)
        print(f"✅ Formatado: {file_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao formatar {file_path}: {e}")

def main():
    project_root = input("Digite o caminho do diretório do projeto (ou pressione Enter para usar o diretório atual): ").strip()
    
    if not project_root:
        project_root = os.getcwd()
    
    print(f"\n🔍 Procurando arquivos Python em: {project_root}")
    python_files = find_python_files(project_root)
    
    if not python_files:
        print("⚠️ Nenhum arquivo Python encontrado.")
        return
    
    print(f"\n📝 Total de arquivos Python encontrados: {len(python_files)}")
    for file in python_files:
        print(f"  - {file}")
    
    confirm = input("\nDeseja formatar todos os arquivos com Black? (s/n): ").strip().lower()
    if confirm != "s":
        print("Operação cancelada.")
        return
    
    print("\n🛠️ Formatando arquivos...")
    for file in python_files:
        format_with_black(file)
    
    print("\n🎉 Concluído!")

if __name__ == "__main__":
    main()