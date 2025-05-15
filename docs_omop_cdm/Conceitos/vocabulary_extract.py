import csv

def generate_vocabulary_script(input_csv_path, output_txt_path):
    try:
        with open(input_csv_path, 'r') as csv_file:
            # Read the CSV file with tab delimiter
            reader = csv.DictReader(csv_file, delimiter='\t')
            
            # Read all rows into a list and sort by vocabulary_concept_id
            sorted_rows = sorted(reader, key=lambda row: int(row['vocabulary_concept_id']))
            
            # Open the output file for writing
            with open(output_txt_path, 'w') as txt_file:
                for row in sorted_rows:
                    # Extract values from the current row
                    vocabulary_id = row['vocabulary_id']
                    vocabulary_name = row['vocabulary_name']
                    vocabulary_concept_id = row['vocabulary_concept_id']
                    
                    # Write the formatted string to the output file
                    txt_file.write(f'vocabulary("{vocabulary_id}", "{vocabulary_name}", {vocabulary_concept_id})\n')
        
        print(f"✔️ Script generated successfully: {output_txt_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

# Example usage
input_csv_path = "/home/guilherme/Documents/MC854/Server/server-saude/docs_omop_cdm/Conceitos/VOCABULARY.csv"  # Replace with the path to your input .csv file
output_txt_path = "/home/guilherme/Documents/MC854/Server/server-saude/docs_omop_cdm/Conceitos/VOCABULARY.txt"  # Replace with the desired output .txt file path
generate_vocabulary_script(input_csv_path, output_txt_path)