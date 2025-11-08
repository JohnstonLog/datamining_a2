Authors: 
- Amaan Hingora 
- Logan Johnston

Overview:

This program implements the FP-Growth (Frequent Pattern Growth) algorithm for mining frequent itemsets from large transactional datasets.
It efficiently avoids candidate generation by compressing the dataset into an FP-tree structure and recursively mining conditional trees.

How It Works:

1. Reads Dataset

    - Supports both formats:

        - tid count item1 item2 ... (first two fields ignored)

        - item1 item2 ... (plain items per line)

    - Skips a header line if it’s a single integer.

2. Builds FP-Tree

    - Counts item frequencies (1st pass).

    - Keeps items meeting minimum support threshold.

    - Inserts each transaction into the FP-tree in descending order of frequency.

3. Mines Frequent Patterns

    - Traverses the FP-tree from least frequent items upward.

    - Builds conditional pattern bases and conditional trees recursively.

4. Outputs Results

    - Results written to: MiningResult_<datasetFileName>.txt

    - File format:

                    |FPs| = <number_of_patterns>
                    a, b, c : <support>
    - Console displays minsup, total patterns, and runtime.


Usage:

python fpgrowth.py <dataset_path> <minsup_percent>


Example Commands:

python fpgrowth.py ./data.txt 50
python fpgrowth.py ./1k5L.txt 3
python fpgrowth.py ./t25i10d10k.txt 5
python fpgrowth.py ./retail.txt 1


Example Files:

Each run creates a file named: MiningResult_<dataset_name>.txt
containing all discovered frequent patterns sorted by size and lexicographically.




