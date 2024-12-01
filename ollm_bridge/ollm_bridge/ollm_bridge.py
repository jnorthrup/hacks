import subprocess
import os
import logging
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OllmBridge")

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

def get_lmstudio_models_dir():
    """Retrieve LMStudio models directory."""
    logger.info("Retrieving LMStudio models directory...")
    models_dir = run_command(["lmstudio", "config", "get", "models_dir"])
    if models_dir:
        logger.info(f"LMStudio models directory: {models_dir}")
    return models_dir

def create_symlinks(ollama_dir, lmstudio_dir, models):
    """Create symbolic links for models at a single level."""
    for model in models:
        model_path = os.path.join(ollama_dir, model)
        symlink_path = os.path.join(lmstudio_dir, model)

        if not os.path.exists(model_path):
            logger.warning(f"Model path does not exist: {model_path}")
            continue

        try:
            if not os.path.exists(symlink_path):
                os.symlink(model_path, symlink_path)
                logger.info(f"Created symlink: {symlink_path} -> {model_path}")
            else:
                logger.info(f"Symlink already exists: {symlink_path}")
        except OSError as e:
            logger.error(f"Failed to create symlink for {model_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Ollm Bridge Single-Level Symlink Creator")
    args = parser.parse_args()

    # Retrieve configurations
    ollama_dir = get_ollama_base_dir()
    lmstudio_dir = get_lmstudio_models_dir()
    models = list_ollama_models()

    if not (ollama_dir and lmstudio_dir and models):
        logger.error("Failed to retrieve configurations. Exiting.")
        return

    # Create symlinks
    create_symlinks(ollama_dir, lmstudio_dir, models)

if __name__ == "__main__":
    main()
