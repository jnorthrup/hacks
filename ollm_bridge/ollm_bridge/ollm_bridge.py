import argparse
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)

def run_command(command):
    """Run a command and return its output."""
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        return None

def get_ollama_base_dir():
    """Retrieve Ollama base directory from CLI."""
    logger.info("Retrieving Ollama base directory...")
    base_dir = run_command(["ollama", "config", "get", "models_dir"])
    if base_dir:
        logger.info(f"Ollama base directory: {base_dir}")
    return base_dir

def list_ollama_models():
    """List available models in Ollama."""
    logger.info("Listing Ollama models...")
    models = run_command(["ollama", "list"])
    if models:
        logger.info(f"Available models: {models.splitlines()}")
        return models.splitlines()
    return []

def get_lmstudio_models_dir():
    """Retrieve LMStudio models directory."""
    logger.info("Retrieving LMStudio models directory...")
    models_dir = run_command(["lmstudio", "config", "get", "models_dir"])
    if models_dir:
        logger.info(f"LMStudio models directory: {models_dir}")
    return models_dir

def create_symlinks(ollama_dir, lmstudio_dir, models):
    """Create symbolic links for models."""
    if not (ollama_dir and lmstudio_dir):
        logger.error("Missing required directories")
        return False
        
    for model in models:
        model_path = os.path.join(ollama_dir, model)
        lmstudio_model_path = os.path.join(lmstudio_dir, model)
        
        if not os.path.exists(model_path):
            logger.warning(f"Model path does not exist: {model_path}")
            continue

        os.makedirs(os.path.dirname(lmstudio_model_path), exist_ok=True)

        try:
            if not os.path.exists(lmstudio_model_path):
                os.symlink(model_path, lmstudio_model_path)
                logger.info(f"Created symlink: {lmstudio_model_path} -> {model_path}")
            else:
                logger.info(f"Symlink already exists: {lmstudio_model_path}")
        except OSError as e:
            logger.error(f"Failed to create symlink for {model_path}: {e}")
            return False
    
    return True

def main(args=None):
    """Main entry point for the Ollm Bridge CLI"""
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Ollm Bridge - Link Ollama models to LMStudio")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args(args)
    
    # Configure logging based on debug flag
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s'
    )
    
    logger.info("Ollm Bridge starting...")
    
    # Retrieve configurations
    ollama_dir = get_ollama_base_dir()
    lmstudio_dir = get_lmstudio_models_dir()
    models = list_ollama_models()

    if not (ollama_dir and lmstudio_dir and models):
        logger.error("Failed to retrieve configurations. Exiting.")
        return 1

    # Create symlinks
    if create_symlinks(ollama_dir, lmstudio_dir, models):
        logger.info("Successfully created model symlinks")
        return 0
    else:
        logger.error("Failed to create some symlinks")
        return 1

if __name__ == "__main__":
    sys.exit(main())
