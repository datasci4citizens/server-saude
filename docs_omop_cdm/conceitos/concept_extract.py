import csv
from pathlib import Path

def generate_add_concept_script(input_csv_path, output_txt_path):
    try:
        with open(input_csv_path, 'r') as csv_file:
            reader = csv.DictReader(csv_file, delimiter='\t')
            # Sort rows by Id (as integer)
            sorted_rows = sorted(reader, key=lambda row: int(row['Id']))
            with open(output_txt_path, 'w') as txt_file:
                for row in sorted_rows:
                    Id = row['Id']
                    Name = row['Name']
                    Standard_Class = row['Standard Class']
                    Code = row['Code']
                    Domain = row['Domain']
                    Vocab = row['Vocab']
                    txt_file.write(f'add_concept({Id}, "{Name}", "{Standard_Class}", "{Code}", "{Domain}", "{Vocab}", )\n')
        print(f"✔️ Script generated successfully: {output_txt_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

# Use current directory for input and output files
current_dir = Path(__file__).parent
input_csv_path = current_dir / "language_concept_id.csv"
output_txt_path = current_dir / "language_concept_id.txt"
generate_add_concept_script(input_csv_path, output_txt_path)