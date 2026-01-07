@Author: Shoaib Rahman
![alt text](image.png)

# Automated Primary Key Discovery Using Hierarchical Sieve and Graph Neural Networks

This project implements an intelligent system for automated primary key discovery in relational databases. It combines a hierarchical heuristic sieve with Graph Attention Networks (GAT) to identify optimal primary key candidates across tables without requiring prior schema knowledge.

## Features

- **Hierarchical Sieve**: Multi-level filtering system that categorizes columns by their naming patterns and uniqueness
  - Level 1: Direct ID columns (e.g., `id`)
  - Level 2: Semantic patterns (e.g., `customer_id`, `order_key`, `uuid`)
  - Level 2.5: Discriminator columns (e.g., `type`, `category`, `created`)
  - Level 3: Structural candidates (high uniqueness but no naming convention)
  - Level 4: Composite key detection (multi-column combinations)

- **Graph Neural Network**: GAT-based model that analyzes schema topology and column relationships
  - Builds graph from table relationships and column name similarity
  - Uses attention mechanisms to learn structural patterns
  - Provides confidence scores for each candidate

- **Smart Ranking**: Combines heuristic and GNN scores to rank candidates
  - Prioritizes semantic IDs with perfect uniqueness
  - Suggests composite keys when single-column candidates are insufficient
  - Provides alternative candidates for review

## Project Structure

```
├── models/
│   ├── gcn_model.py          # GCN-based model (alternative)
│   └── __init__.py
├── scripts/
│   ├── __init__.py
│   ├── gat_model.py          # GAT model architecture
│   ├── gnn_pipeline.py       # GNN inference pipeline
│   ├── heuristic_filter.py   # Hierarchical sieve implementation
│   ├── graph_builder.py      # Schema graph construction
│   ├── table_identifier.py   # Database metadata extraction
│   ├── utils.py              # Utility functions
│   └── validation.py         # Candidate validation
├── config.py                 # Configuration management
├── db_connector.py           # Database connection with SQLAlchemy
├── main.py                   # Main entry point
├── requirements.install      # Python dependencies
├── Dockerfile               
├── docker-compose.yml
└── Makefile
```

## Installation

### Local Setup

1. Clone this repository:
```bash
git clone https://github.com/shoaibswe/auto_pk_generator_using_heuristic_and_gnn.git
cd auto_pk_generator_using_heuristic_and_gnn/codes
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.install
```

4. Configure database connection:
Create a `.env` file with your database credentials:
```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=your_database
```

### Docker Setup

Pull from Docker Hub:
```bash
docker pull shoaibswe/generate_primary_key
```

## Usage

### Running Locally

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Run the main pipeline
python main.py
```

### Running with Docker Compose

1. Build and run containers:
```bash
make compose-up
```

2. Verify containers are running:
```bash
docker ps
```

3. View application logs:
```bash
docker logs python_app_container
```

4. Stop services:
```bash
make compose-down
```

## Output

The system produces a ranked table of primary key candidates:

```
TABLE                | PRIORITY     | TYPE            | CANDIDATE COLS                  | HEUR   | GNN    | RANK   | DECISION
=================================================================================================================================
customers            | PRIMARY      | Semantic        | customer_id                     | 0.50 | 0.99 | 2.99 | ENFORCE PK
customers            | ALT 1        | Composite       | customer_id, last_name          | 0.45 | 0.74 | 1.94 | ALT CANDIDATE
customers            | ALT 2        | Structural      | address                         | 0.33 | 0.72 | 0.72 | ALT CANDIDATE
```

### Decision Types
- **ENFORCE PK**: High confidence (GNN ≥ 0.90), recommended for immediate implementation
- **SUGGESTED PK**: Good confidence (GNN < 0.90), requires review
- **ALT CANDIDATE**: Alternative options for consideration

## Technology Stack

- **Python 3.12+**
- **PyTorch & PyTorch Geometric**: GNN implementation
- **SQLAlchemy**: Database connectivity
- **PostgreSQL**: Primary database support
- **NumPy & Pandas**: Data processing
- **python-Levenshtein**: String similarity

## Algorithm Overview

1. **Data Loading**: Connects to database and loads table metadata
2. **Hierarchical Sieve**: Filters columns based on uniqueness and naming patterns
3. **Graph Construction**: Builds schema graph using LSH and column name similarity
4. **GNN Inference**: GAT model analyzes graph structure and predicts confidence scores
5. **Ranking & Display**: Combines heuristic and GNN scores to rank and present candidates

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

[Add your license information here]

## Author

Shoaib Rahman - [GitHub](https://github.com/shoaibswe)
