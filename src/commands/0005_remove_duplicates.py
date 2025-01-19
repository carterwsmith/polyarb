import pandas as pd


def remove_duplicates(input_path, output_path) -> int:
    df = pd.read_csv(input_path)
    df_cleaned = df.drop_duplicates()
    df_cleaned.to_csv(output_path, index=False)

    return len(df) - len(df_cleaned)
