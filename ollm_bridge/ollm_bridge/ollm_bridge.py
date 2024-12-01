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

def import_model(model_path: str, cli_path: str, cli_name: str) -> bool:
    """Import a model using the specified CLI tool."""
    logger.info(f"Importing model using {cli_name}: {model_path}")
    result = run_command([cli_path, "import", model_path])
    if result:
        logger.info(f"Successfully imported model: {model_path}")
        return True
    logger.error(f"Failed to import model: {model_path}")
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

def create_symlinks(source_dir: str, target_dir: str, models: List[str],
                   link_type: str = 'soft', force: bool = False):
    """Create links for models with specified link type."""
    logger.debug(f"Creating {link_type} links from {source_dir} to {target_dir}")
    
    for model in models:
        model_dir = os.path.join(target_dir, model)
        os.makedirs(model_dir, exist_ok=True)
        
        model_files = get_model_files(source_dir, model)
        
        if not model_files:
            logger.warning(f"No files found for model: {model}")
            continue
            
        for src_file in model_files:
            target_path = os.path.join(model_dir, os.path.basename(src_file))
            
            # Handle existing links/files
            if os.path.exists(target_path):
                if force:
                    try:
                        os.unlink(target_path)
                    except OSError as e:
                        logger.error(f"Failed to remove existing link: {e}")
                        continue
                else:
                    logger.debug(f"Skipping existing link: {target_path}")
                    continue
            
            try:
                if link_type == 'hard':
                    os.link(src_file, target_path)
                elif link_type == 'ntfs' and os.name == 'nt':
                    run_command(["mklink", target_path, src_file])
                else:  # soft link (default)
                    os.symlink(src_file, target_path)
                    
                logger.info(f"Created {link_type} link: {target_path} -> {src_file}")
            except OSError as e:
                logger.error(f"Failed to create {link_type} link for {src_file}: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Create symbolic links between Ollama and LMStudio models",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('-i', '--interactive', action='store_true', help='Enable interactive model selection')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without making them')
    
    # Add new bidirectional options
    parser.add_argument('--direction', choices=['ollama-to-lmstudio', 'lmstudio-to-ollama'],
                       default='ollama-to-lmstudio', help='Direction of model linking')
    parser.add_argument('--link-type', choices=['soft', 'hard', 'ntfs'],
                       default='soft', help='Type of link to create')
    parser.add_argument('--force', action='store_true', help='Force overwrite existing links')
    parser.add_argument('--import-only', action='store_true', help='Only import models, no linking')
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
        
    # Check LM Studio version
    if not check_lmstudio_version():
        logger.error("LM Studio version check failed. Exiting.")
        return
        
    # Determine source and target based on direction
    if args.direction == 'lmstudio-to-ollama':
        source_dir = get_lmstudio_models_dir()
        target_dir = get_ollama_models_dir()
        cli_path = "ollama"
        cli_name = "Ollama"
        models = list_ollama_models()
    else:  # ollama-to-lmstudio
        source_dir = get_ollama_models_dir()
        target_dir = get_lmstudio_models_dir()
        cli_path = get_lmstudio_cli_path()
        cli_name = "LMStudio"
        models = list_ollama_models()

    if not (source_dir and target_dir and models):
        logger.error("Failed to retrieve configurations. Exiting.")
        return

    # Check directory permissions
    if not check_directory_permissions(target_dir):
        logger.error(f"Insufficient permissions for {cli_name} directory. Exiting.")
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
            model_files = get_model_files(source_dir, model)
            for src_file in model_files:
                target_path = os.path.join(target_dir, model, os.path.basename(src_file))
                logger.info(f"Would create: {target_path} -> {src_file}")
        return

    if args.import_only:
        for model in models:
            model_files = get_model_files(source_dir, model)
            for file in model_files:
                import_model(file, cli_path, cli_name)
        return

    if args.dry_run:
        logger.info("Dry run mode - previewing changes:")
        for model in models:
            model_files = get_model_files(source_dir, model)
            for src_file in model_files:
                target_path = os.path.join(target_dir, model, os.path.basename(src_file))
                logger.info(f"Would create: {target_path} -> {src_file}")
        return

    create_symlinks(source_dir, target_dir, models,
                   link_type=args.link_type, force=args.force)

if __name__ == "__main__":
    main()
