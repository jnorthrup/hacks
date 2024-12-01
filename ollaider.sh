#!/bin/bash
set -x
# Define the output file
output_file=".aider.model.metadata.json"

# Initialize the JSON object
echo "{" > $output_file

# Retrieve the list of models
models=$(ollama list | awk 'NR>1 {print $1}')

# Iterate over each model to extract details
for model in $models; do
  # Extract model information
  info=$(ollama show "$model" 2>/dev/null)

  # Check if the model information was retrieved successfully
  if [ $? -ne 0 ]; then
    echo "Warning: Failed to retrieve information for model '$model'. Skipping."
    continue
  fi

  # Extract parameters using grep and awk
  parameters=$(echo "$info" | grep -i 'parameters' | awk '{print $2}')
  context_length=$(echo "$info" | grep -i 'context length' | awk '{print $3}')
  embedding_length=$(echo "$info" | grep -i 'embedding length' | awk '{print $3}')
  quantization=$(echo "$info" | grep -i 'quantization' | awk '{print $2}')

  # Set default values for cost per token
  input_cost_per_token=0.00000014
  output_cost_per_token=0.00000028

  # Append model details to the JSON object
  cat <<EOT >> $output_file
  "ollama/$model": {
    "max_tokens": $context_length,
    "max_input_tokens": $context_length,
    "max_output_tokens": $context_length,
    "input_cost_per_token": $input_cost_per_token,
    "output_cost_per_token": $output_cost_per_token,
    "litellm_provider": "ollama",
    "mode": "chat"
  },
EOT
done

# Remove the trailing comma and close the JSON object
sed -i '' -e '$ s/,$//' $output_file
echo "}" >> $output_file

echo "Model metadata has been written to $output_file"
