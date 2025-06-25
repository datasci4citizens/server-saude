from pathlib import Path
import csv

def generate_concept_class_script(input_csv_path, output_txt_path):
    try:
        with open(input_csv_path, 'r') as csv_file:
            # Read the CSV file with tab delimiter
            reader = csv.DictReader(csv_file, delimiter='\t')
            
            # Read all rows into a list and sort by concept_class_concept_id
            sorted_rows = sorted(reader, key=lambda row: int(row['concept_class_concept_id']))
            
            # Open the output file for writing
            with open(output_txt_path, 'w') as txt_file:
                for row in sorted_rows:
                    # Extract values from the current row
                    concept_class_id = row['concept_class_id']
                    concept_class_name = row['concept_class_name']
                    concept_class_concept_id = row['concept_class_concept_id']
                    
                    # Write the formatted string to the output file
                    txt_file.write(f'concept_class("{concept_class_id}", "{concept_class_name}", {concept_class_concept_id})\n')
        
        print(f"✔️ Script generated successfully: {output_txt_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

current_dir = Path(__file__).parent
input_csv_path = current_dir / "CONCEPT_CLASS.csv"
output_txt_path = current_dir / "CONCEPT_CLASS.txt"
generate_concept_class_script(input_csv_path, output_txt_path)