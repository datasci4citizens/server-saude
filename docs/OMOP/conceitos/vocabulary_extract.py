import csv
from pathlib import Path


def generate_vocabulary_script(input_csv_path, output_txt_path):
    try:
        with open(input_csv_path, "r") as csv_file:
            # Read the CSV file with tab delimiter
            reader = csv.DictReader(csv_file, delimiter="\t")

            # Read all rows into a list and sort by vocabulary_concept_id
            sorted_rows = sorted(reader, key=lambda row: int(row["vocabulary_concept_id"]))

            # Open the output file for writing
            with open(output_txt_path, "w") as txt_file:
                for row in sorted_rows:
                    # Extract values from the current row
                    vocabulary_id = row["vocabulary_id"]
                    vocabulary_name = row["vocabulary_name"]
                    vocabulary_concept_id = row["vocabulary_concept_id"]

                    # Write the formatted string to the output file
                    txt_file.write(f'vocabulary("{vocabulary_id}", "{vocabulary_name}", {vocabulary_concept_id})\n')

        print(f"✔️ Script generated successfully: {output_txt_path}")
    except Exception as e:
        print(f"❌ Error: {e}")


# Use current directory for input and output files
current_dir = Path(__file__).parent
input_csv_path = current_dir / "VOCABULARY.csv"
output_txt_path = current_dir / "VOCABULARY.txt"
generate_vocabulary_script(input_csv_path, output_txt_path)
