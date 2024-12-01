import subprocess
import os
import logging
import argparse
from typing import Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OllmBridge")

def run_command(command, debug=False):
    """Run a command and return its output."""
    try:
        logger.debug(f"Running command: {command}")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if debug:
            logger.debug(f"Command stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"Command stderr: {result.stderr}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        if debug:
            logger.debug(f"Command stderr: {e.stderr}")
        return None

def get_ollama_models_dir():
    """Retrieve Ollama models directory."""
    # Check environment variable first
    base_dir = os.environ.get("OLLAMA_MODELS")
    if base_dir:
        logger.info(f"Using OLLAMA_MODELS environment variable: {base_dir}")
        return base_dir
        
    # Platform-specific paths
    if os.name == 'nt':  # Windows
        base_dir = os.path.expandvars(r'C:\Users\%USERNAME%\.ollama\models')
    elif os.name == 'posix':  # macOS and Linux
        if os.path.exists('/usr/share/ollama'):  # Linux
            base_dir = '/usr/share/ollama/.ollama/models'
        else:  # macOS
            base_dir = os.path.expanduser('~/.ollama/models')
    
    if os.path.exists(base_dir):
        logger.info(f"Using Ollama base directory: {base_dir}")
        return base_dir
    
    logger.error("Ollama models directory not found")
    return None

def list_ollama_models():
    """List models using Ollama CLI."""
    result = run_command(["ollama", "list"])
    if not result:
        return []
        
    models = []
    for line in result.splitlines()[1:]:  # Skip header line
        parts = line.split()
        if parts:
            models.append(parts[0])  # First column is model name
    return models

def check_directory_permissions(directory: str) -> bool:
    """Check if we have proper permissions for the directory."""
    try:
        test_file = os.path.join(directory, '.permission_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except (IOError, OSError) as e:
        logger.error(f"Permission error for directory {directory}: {e}")
        return False

def validate_model_format(model_path: str) -> bool:
    """Validate if model file is in supported format."""
    supported_extensions = ['.gguf', '.ggml']
    ext = os.path.splitext(model_path)[1].lower()
    return ext in supported_extensions

def check_lmstudio_version() -> bool:
    """Check LM Studio version and compatibility."""
    lmstudio_cli = get_lmstudio_cli_path()
    version = run_command([lmstudio_cli, "version"])
    if version:
        logger.info(f"LM Studio version: {version}")
        # Add version compatibility logic here
        return True
    return False

def get_lmstudio_cli_path() -> str:
    """Get the platform-specific LM Studio CLI path."""
    if os.name == 'nt':  # Windows
        return 'lmstudio'  # Assuming it's in PATH
    elif os.name == 'posix':  # macOS and Linux
        if os.path.exists('/usr/share/ollama'):  # Linux
            return 'lmstudio'  # Assuming it's in PATH
        else:  # macOS
            return os.path.expanduser('~/.cache/lm-studio/bin/lms')
    return 'lmstudio'  # Default fallback

def get_lmstudio_models_dir():
    """Retrieve LM Studio models directory using CLI."""
    lmstudio_cli = get_lmstudio_cli_path()
    models_dir = run_command([lmstudio_cli, "config", "get", "models_dir"])
    if models_dir:
        logger.info(f"LM Studio models directory: {models_dir}")
        return models_dir
    logger.error("Could not determine LM Studio models directory")
    return None

def get_model_files(ollama_dir: str, model_name: str) -> List[str]:
    """Get the actual model files with format validation."""
    manifest_dir = os.path.join(ollama_dir, "manifests", "registry.ollama.ai")
    
    # Check both library and custom paths
    possible_paths = [
        os.path.join(manifest_dir, "library", model_name),
        os.path.join(manifest_dir, model_name),
    ]
    
    files = []
    for path in possible_paths:
        if os.path.exists(path):
            for root, _, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if validate_model_format(file_path):
                        files.append(file_path)
                    else:
                        logger.warning(f"Skipping unsupported format: {file_path}")
                    
    return files

def create_symlinks(ollama_dir, lmstudio_dir, models):
    """Create symbolic links for models."""
    logger.debug(f"Creating symlinks from {ollama_dir} to {lmstudio_dir}")
    
    for model in models:
        # Create model directory in LMStudio
        model_dir = os.path.join(lmstudio_dir, model)
        os.makedirs(model_dir, exist_ok=True)
        
        # Get model files
        model_files = get_model_files(ollama_dir, model)
        
        if not model_files:
            logger.warning(f"No files found for model: {model}")
            continue
            
        # Create symlinks for each file
        for src_file in model_files:
            # Create relative path structure in target
            rel_path = os.path.relpath(src_file, os.path.join(ollama_dir, "manifests"))
            target_path = os.path.join(model_dir, os.path.basename(src_file))
            
            try:
                if not os.path.exists(target_path):
                    os.symlink(src_file, target_path)
                    logger.info(f"Created symlink: {target_path} -> {src_file}")
                else:
                    logger.debug(f"Symlink already exists: {target_path}")
            except OSError as e:
                logger.error(f"Failed to create symlink for {src_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Create symbolic links from Ollama models to LMStudio")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('-i', '--interactive', action='store_true', help='Enable interactive model selection')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without making them')
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
        
    # Check LM Studio version
    if not check_lmstudio_version():
        logger.error("LM Studio version check failed. Exiting.")
        return
        
    # Retrieve configurations
    ollama_dir = get_ollama_models_dir()
    lmstudio_dir = get_lmstudio_models_dir()
    models = list_ollama_models()

    if not (ollama_dir and lmstudio_dir and models):
        logger.error("Failed to retrieve configurations. Exiting.")
        return

    # Check directory permissions
    if not check_directory_permissions(lmstudio_dir):
        logger.error("Insufficient permissions for LM Studio directory. Exiting.")
        return

    # Handle interactive mode
    if args.interactive:
        print("\nAvailable models:")
        for i, model in enumerate(models, 1):
            print(f"{i}. {model}")
        choices = input("\nEnter numbers of models to link (space-separated) or press Enter for all: ").strip()
        
        if choices:
            try:
                selected_indices = [int(i)-1 for i in choices.split() if i.isdigit()]
                models = [models[i] for i in selected_indices if 0 <= i < len(models)]
            except (ValueError, IndexError):
                logger.error("Invalid selection. Using all models.")

    # Handle dry run mode
    if args.dry_run:
        logger.info("Dry run mode - previewing changes:")
        for model in models:
            model_files = get_model_files(ollama_dir, model)
            for src_file in model_files:
                target_path = os.path.join(lmstudio_dir, model, os.path.basename(src_file))
                logger.info(f"Would create: {target_path} -> {src_file}")
        return

    # Create symlinks
    create_symlinks(ollama_dir, lmstudio_dir, models)

if __name__ == "__main__":
    main()
