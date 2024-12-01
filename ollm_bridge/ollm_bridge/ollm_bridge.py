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
    if models:
        logger.info(f"Available models: {models.splitlines()}")
    return models.splitlines() if models else []

def get_lmstudio_models_dir(debug=False):
    """Retrieve LMStudio models directory."""
    logger.info("Retrieving LMStudio models directory...")
    models_dir = run_command(["lmstudio", "config", "get", "models_dir"], debug=debug)
    if models_dir:
        logger.info(f"LMStudio models directory: {models_dir}")
    return models_dir

def create_symlinks(ollama_dir, lmstudio_dir, models):
    """Create symbolic links for models at a single level."""
    logger.debug(f"Creating symlinks from {ollama_dir} to {lmstudio_dir}")
    logger.debug(f"Models to process: {models}")
    
    for model in models:
        model_path = os.path.join(ollama_dir, model)
        symlink_path = os.path.join(lmstudio_dir, model)
        logger.debug(f"Processing model: {model}")
        logger.debug(f"Source path: {model_path}")
        logger.debug(f"Target path: {symlink_path}")

        if not os.path.exists(model_path):
            logger.warning(f"Model path does not exist: {model_path}")
            continue

        try:
            if not os.path.exists(symlink_path):
                os.symlink(model_path, symlink_path)
                logger.info(f"Created symlink: {symlink_path} -> {model_path}")
            else:
                logger.debug(f"Symlink already exists: {symlink_path}")
        except OSError as e:
            logger.error(f"Failed to create symlink for {model_path}: {e}")

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
