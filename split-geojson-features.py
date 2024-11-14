#!/usr/bin/env python3

import click
import json
import os
from pathlib import Path

def load_feature_collection(input_file: str) -> dict:
    """
    Loads the GeoJSON Feature Collection file.

    Parameters:
    - input_file (str): Path to the GeoJSON Feature Collection.

    Returns:
    - dict: Parsed JSON content of the feature collection.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get("type") != "FeatureCollection" or "features" not in data:
            raise ValueError("The provided file is not a valid GeoJSON Feature Collection.")
        return data
    except Exception as e:
        click.echo(f"Error loading Feature Collection file: {e}", err=True)
        raise

@click.command()
@click.argument('input_file', type=click.Path(exists=True, readable=True))
@click.argument('output_directory', type=click.Path(file_okay=False, writable=True))
def main(input_file, output_directory):
    """
    Load a GeoJSON Feature Collection from INPUT_FILE and output each feature as a separate JSON
    into the OUTPUT_DIRECTORY.
    """
    try:
        feature_collection = load_feature_collection(input_file)
    except Exception:
        click.echo("Failed to load the Feature Collection.", err=True)
        return

    features = feature_collection.get("features", [])

    if not features:
        click.echo("No features found in the collection.", err=True)
        return

    # Create the output directory if it doesn't exist
    Path(output_directory).mkdir(parents=True, exist_ok=True)

    # Iterate over each feature and save it as a separate JSON file
    for index, feature in enumerate(features):
        feature_id = feature.get("id", f"feature_{index}")
        output_file_path = os.path.join(output_directory, f"{feature_id}.json")

        # Write feature to JSON file
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(feature, f, indent=2)
            click.echo(f"Feature saved to: {output_file_path}")
        except Exception as e:
            click.echo(f"Error writing feature {feature_id} to file: {e}", err=True)

if __name__ == "__main__":
    main()
