import os
from PIL import Image
import pytesseract
from pathlib import Path
import json
from typing import Dict, List
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

def process_image(args) -> tuple:
    """
    Process a single image file.
    
    Args:
        args: Tuple of (filename, input_dir, output_dir)
    Returns:
        Tuple of (filename, extracted_text)
    """
    filename, input_dir, output_dir = args
    try:
        # Full path to image
        image_path = os.path.join(input_dir, filename)
        
        # Open and process image
        with Image.open(image_path) as img:
            # Extract text using pytesseract
            text = pytesseract.image_to_string(img)
            
            # Save individual text file
            text_filename = Path(filename).stem + '.txt'
            text_path = os.path.join(output_dir, text_filename)
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
                
        print(f"Processed: {filename}")
        return filename, text
        
    except Exception as e:
        print(f"Error processing {filename}: {str(e)}")
        return filename, f"ERROR: {str(e)}"

def process_directory(input_dir: str, output_dir: str, max_workers: int = None) -> Dict[str, str]:
    """
    Process all JPEG files in a directory and perform OCR using multiple processes.
    
    Args:
        input_dir: Directory containing JPEG files
        output_dir: Directory to save OCR results
        max_workers: Maximum number of worker processes (defaults to CPU count)
        
    Returns:
        Dictionary mapping filenames to extracted text
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # If max_workers not specified, use CPU count
    if max_workers is None:
        max_workers = multiprocessing.cpu_count()
    
    # Supported image extensions
    valid_extensions = {'.jpg', '.jpeg', '.JPG', '.JPEG'}
    
    # Get list of valid image files
    image_files = [
        f for f in os.listdir(input_dir) 
        if Path(f).suffix in valid_extensions
    ]
    
    # Prepare arguments for worker processes
    work_args = [(f, input_dir, output_dir) for f in image_files]
    
    # Process files concurrently
    results = {}
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for filename, text in executor.map(process_image, work_args):
            results[filename] = text
    
    # Save consolidated results to JSON
    json_path = os.path.join(output_dir, 'ocr_results.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Perform OCR on all JPEG files in a directory')
    parser.add_argument('input_dir', help='Input directory containing JPEG files')
    parser.add_argument('output_dir', help='Output directory for OCR results')
    parser.add_argument('--workers', type=int, help='Number of worker processes (default: CPU count)',
                      default=None)
    
    args = parser.parse_args()
    
    results = process_directory(args.input_dir, args.output_dir, args.workers)
    print(f"\nProcessed {len(results)} files. Results saved to {args.output_dir}")
