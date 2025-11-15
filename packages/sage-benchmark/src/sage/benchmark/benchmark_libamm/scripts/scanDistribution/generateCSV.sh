#!/bin/bash

source_file="tag.txt"

while IFS= read -r line; do
  # Define the filename based on the line content
  filename="config_${line}.csv"

  # Create the file with the desired content
  echo "key,value,type" > "$filename"


  # Append the common content
  echo "aRow,1000,U64" >> "$filename"
  echo "aCol,1000,U64" >> "$filename"
  echo "bCol,1000,U64" >> "$filename"
  echo "sketchDimension,25,U64" >> "$filename"
  echo "ptFile,torchscripts/FDAMM.pt,String" >> "$filename"
  echo "useCPP,1,U64" >> "$filename"
  echo "cppAlgoTag,$line,String" >> "$filename"
  echo "threads,1,U64" >> "$filename"
  echo "forceMP,1,U64" >> "$filename"
done < "$source_file"
