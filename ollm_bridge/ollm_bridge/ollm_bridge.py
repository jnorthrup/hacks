import subprocess
import os
import logging
import argparse

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

def get_ollama_base_dir(debug=False):
    """Retrieve Ollama base directory."""
    logger.info("Retrieving Ollama base directory...")
    
    # First check OLLAMA_MODELS environment variable
    base_dir = os.environ.get("OLLAMA_MODELS")
    if base_dir:
        logger.info(f"Using OLLAMA_MODELS environment variable: {base_dir}")
        return base_dir
        
    # If env var not set, use platform-specific default paths
    if os.name == 'nt':  # Windows
        base_dir = os.path.expandvars(r'C:\Users\%USERNAME%\.ollama\models')
    elif os.name == 'posix':  # macOS and Linux
        if os.path.exists('/usr/share/ollama'):  # Linux
            base_dir = '/usr/share/ollama/.ollama/models'
        else:  # macOS
            base_dir = os.path.expanduser('~/.ollama/models')
    
    if base_dir:
        logger.info(f"Using default Ollama base directory: {base_dir}")
    else:
        logger.error("Could not determine Ollama models directory")
        
    return base_dir

def list_ollama_models(debug=False):
    """List available models in Ollama."""
    logger.info("Listing Ollama models...")
    models = run_command(["ollama", "list"], debug=debug)
    if not models:
        return []
        
    # Parse the output to get model names
    model_list = []
    for line in models.splitlines()[1:]:  # Skip header line
        parts = line.split()
        if parts:
            model_list.append(parts[0])  # First column is model name
            
    logger.info(f"Found models: {model_list}")
    return model_list

def get_lmstudio_models_dir(debug=False):
    """Retrieve LMStudio models directory."""
    logger.info("Retrieving LMStudio models directory...")
    models_dir = run_command(["lmstudio", "config", "get", "models_dir"], debug=debug)
    if models_dir:
        logger.info(f"LMStudio models directory: {models_dir}")
    return models_dir

def get_model_files(ollama_dir, model_name, debug=False):
    """Get the actual model files for a given model name."""
    manifest_dir = os.path.join(ollama_dir, "manifests", "registry.ollama.ai")
    
    # Handle both library and custom namespaces
    possible_paths = [
        os.path.join(manifest_dir, "library", model_name),
        os.path.join(manifest_dir, model_name),
    ]
    
    model_files = []
    for path in possible_paths:
        if os.path.exists(path):
            # Get all files in the manifest directory
            for root, _, files in os.walk(path):
                for file in files:
                    model_files.append(os.path.join(root, file))
                    
    if debug:
        logger.debug(f"Found model files for {model_name}: {model_files}")
        
    return model_files

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
    parser = argparse.ArgumentParser(description="Ollm Bridge - Create symbolic links from Ollama models to LMStudio")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
        
    # Retrieve configurations
    ollama_dir = get_ollama_base_dir(debug=args.debug)
    lmstudio_dir = get_lmstudio_models_dir(debug=args.debug)
    models = list_ollama_models(debug=args.debug)

    if not (ollama_dir and lmstudio_dir and models):
        logger.error("Failed to retrieve configurations. Exiting.")
        return

    # Create symlinks
    create_symlinks(ollama_dir, lmstudio_dir, models)

if __name__ == "__main__":
    main()
