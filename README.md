# Real-Time Crypto Analytics Platform

A high-performance, open-source platform for real-time cryptocurrency analytics. Built entirely on **AWS**, this project provides a scalable, end-to-end solution to ingest, process, and visualize live market data from major exchanges.

Whether you're a developer, data analyst, or crypto enthusiast, this platform provides the tools to uncover market insights with **sub-second latency**.


## 🏗️ Architecture

The platform uses a scalable, event-driven architecture on AWS to ensure low latency and high availability, from ingestion to visualization.

```mermaid
graph TD
    subgraph " "
        A["📈<br>Crypto Exchanges<br>(Binance, Coinbase)"]
    end

    subgraph "Ingest & Process"
        A -- WebSocket --> B["🚰<br>Kinesis<br>Data Stream"];
        B -- Real-time Trigger --> C["λ<br>Lambda<br>Validation/Enrichment"];
    end

    subgraph "Store & Transform"
        C --> D["📦<br>S3 Data Lake<br>Partitioned Parquet"];
        D -- ETL Job --> E["✨<br>AWS Glue<br>OHLCV Aggregation"];
    end

    subgraph "Analyze & Visualize"
        E -- Transformed Data --> F["🗄️<br>Redshift<br>Data Warehouse"];
        F -- SQL Queries --> G["📊<br>QuickSight<br>Dashboards"];
    end

    subgraph "Monitor"
        C -- Logs & Metrics --> H["⚙️<br>CloudWatch<br>Alerting & Dashboards"];
        B -- Metrics --> H;
        F -- Metrics --> H;
    end
```

---

## ✨ Key Features

* **⚡ Real-Time Processing**: Ingest and process thousands of records per minute with sub-second latency.
* **🔌 Multi-Exchange Support**: Connects to major exchanges like Binance and Coinbase out-of-the-box.
* **⚙️ Automated ETL**: Automatically aggregates raw trades into OHLCV candlesticks (5m, 15m, 1h) and calculates technical indicators (SMA, EMA, etc.).
* **🚀 High-Performance Analytics**: A Redshift data warehouse optimized for fast, complex queries on large datasets.
* **📊 Rich Visualizations**: Live QuickSight dashboards for market analysis, system monitoring, and data quality checks.
* **💰 Cost-Optimized**: Built with serverless-first principles and cost-saving strategies like Spot Instances and data tiering.
* **🔒 Secure by Design**: Follows security best practices, including least-privilege IAM roles, VPC isolation, and full encryption.

---

## 🛠️ Technology Stack

* **Cloud Provider**: AWS
* **Infrastructure as Code**: Terraform
* **Programming Language**: Python 3.9+
* **Data Ingestion**: Kinesis Data Streams
* **Stream Processing**: Lambda
* **Data Lake**: S3, Glue Data Catalog, Parquet
* **ETL**: AWS Glue
* **Data Warehouse**: Amazon Redshift
* **Visualization**: Amazon QuickSight
* **Monitoring**: CloudWatch
* **Containerization**: Docker

---

## 🚀 Getting Started

### Prerequisites

* An AWS Account with appropriate permissions
* [AWS CLI](https://aws.amazon.com/cli/) configured
* [Terraform](https://www.terraform.io/downloads.html) v1.0+
* [Python](https://www.python.org/downloads/) 3.9+
* [Docker](https://www.docker.com/products/docker-desktop) & Docker Compose

### 1. Local Development Setup

Set up and run the environment locally for testing and development.

```bash
# Clone the repository
git clone [https://github.com/SangramSA/crypto-analytics-dashboard.git](https://github.com/SangramSA/crypto-analytics-dashboard.git)
cd crypto-analytics-dashboard

# Set up environment variables
# This file contains credentials and configurations for the services.
cp .env.example .env
nano .env # Edit with your AWS credentials and custom configuration

# Start the local stack (if applicable for local testing)
docker-compose up -d
```

### 2. Production Deployment

Deploy the full infrastructure to your AWS account using Terraform.

```bash
# Navigate to the Terraform directory
cd infrastructure/terraform

# Initialize Terraform and review the deployment plan
terraform init
terraform plan

# Apply the configuration to deploy the infrastructure
terraform apply

# Deploy the Lambda functions using the provided script
./infrastructure/scripts/deploy.sh

# Start the Kinesis data producer to begin ingestion
python src/ingestion/producers/kinesis_producer.py
```

---

## 🧪 Testing

The project includes a comprehensive test suite to ensure code quality and reliability.

```bash
# Run all unit tests
python -m pytest tests/unit/

# Run integration tests (requires a deployed environment)
python -m pytest tests/integration/

# Run security scans to check for vulnerabilities
bandit -r src/
trivy fs .
```

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

Please follow these steps:

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

Please read [CONTRIBUTING.md](https://github.com/SangramSA/crypto-analytics-dashboard/blob/main/CONTRIBUTING.md%20) for the full guide on our development process and standards.

---

## 📄 License

This project is distributed under the MIT License. See the `LICENSE` file for more information.

---

## 🆘 Support

If you encounter any issues or have questions, please file an issue on the [GitHub Issues](https://github.com/SangramSA/crypto-analytics-dashboard/issues) page.
