import csv

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

# Example usage:
input_csv_path = "/home/guilherme/Documents/MC854/Server/server-saude/docs_omop_cdm/Conceitos/language_concept_id.csv"  # Replace with the path to your input .csv file
output_txt_path = "/home/guilherme/Documents/MC854/Server/server-saude/docs_omop_cdm/Conceitos/language_concept_id.txt"  # Replace with the desired output .txt file path
generate_add_concept_script(input_csv_path, output_txt_path)