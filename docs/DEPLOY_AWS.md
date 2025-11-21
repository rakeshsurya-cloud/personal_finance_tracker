# Deploying to AWS ☁️

You can deploy this app to AWS so your brother in Australia can access it easily.

## Prerequisites
1.  **AWS Account**: You need an active AWS account.
2.  **AWS CLI**: Installed and configured on your machine.

## Option 1: AWS App Runner (Easiest & Best) 🚀
**⚠️ COST WARNING**: This option costs about **$50/month** to run 24/7. Only use this if you are okay with the price for convenience.

Since your code is on GitHub, this is the fastest way.

1.  **Go to AWS App Runner Console**.
2.  **Click "Create Service"**.
3.  **Source**: Select **"Source Code Repository"**.
4.  **Connect GitHub**:
    - Click "Add Connection" and login to GitHub.
    - Select your repo: `rakeshsurya-cloud/personal_finance_tracker`.
    - Branch: `main`.
5.  **Configure Build**:
    - **Runtime**: Python 3
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: `streamlit run app.py --server.port 8080`
    - **Port**: `8080`
6.  **Environment Variables** (Optional for S3):
    - Add `S3_BUCKET` = `your-bucket-name` (if you created one).
    - Add `AWS_REGION` = `us-east-1` (or your region).
7.  **Click "Create & Deploy"**.

Your app will be live in ~5 minutes!

## Option 2: EC2 (Virtual Machine) 💻
If you want full control (like a remote computer).

1.  **Launch an Instance**:
    - Go to EC2 Console -> Launch Instance.
    - Choose "Ubuntu" or "Amazon Linux".
    - Allow Traffic: Check "Allow HTTP" and "Allow HTTPS".
    - **Security Group**: Add a Custom TCP Rule for port `8501` (Source: Anywhere `0.0.0.0/0`).
2.  **Connect to Instance**:
    - SSH into your instance.
3.  **Install & Run**:
    ```bash
    # Update and install git/python
    sudo apt-get update
    sudo apt-get install python3-pip git -y
    
    # Clone your code (or copy it over)
    git clone <your-repo-url>
    cd <your-repo-folder>
    
    # Install dependencies
    pip3 install -r requirements.txt
    
    # Run the app (in background)
    nohup streamlit run app.py &
    ```
4.  **Access**:
    - Visit `http://<your-ec2-public-ip>:8501`

## 💸 How to do it for FREE (AWS Free Tier)
AWS offers a **Free Tier** for 12 months for new accounts.
- **Service**: **EC2** (Virtual Machine).
- **Instance Type**: Select **`t2.micro`** or **`t3.micro`** when launching.
- **Cost**: $0 for the first 12 months (up to 750 hours/month, which is enough to run 1 app 24/7).
- **After 12 months**: It will cost ~$8-10/month.

> **Is t2.micro enough?** 🤔
> **Yes!** For a personal family app (up to ~50,000 transactions), 1 GB of RAM is plenty.
> If you upload huge files (millions of rows), it might crash. In that case, just upgrade to `t3.small` (2 GB RAM).

> **Alternative**: **Streamlit Community Cloud** is free **forever**, but your data might reset if the app goes to sleep. For a family app with persistent data, AWS EC2 (Free Tier) is better, but requires more setup.

## ⚠️ Important Security Note
Deploying to AWS makes your app **publicly accessible** to anyone with the link.
- **Strong Password**: Ensure your `app.py` password is very strong.
- **HTTPS**: App Runner gives you HTTPS automatically (secure). EC2 requires manual setup (e.g., using Nginx/Certbot).

## 🌐 Custom Domain (`srsfiapp.com`)
To use your own domain like `srsfiapp.com`:

1.  **Buy the Domain**: Purchase `srsfiapp.com` on **AWS Route 53** (or GoDaddy/Namecheap).
2.  **Link to App Runner**:
    - Go to your App Runner Service.
    - Click **"Custom Domains"** tab.
    - Click **"Link Domain"**.
    - Enter `srsfiapp.com`.
    - App Runner will give you some DNS records (CNAME/A records).
3.  **Update DNS**:
    - Go to Route 53 (or your registrar).
    - Add the records provided by App Runner.
    - Wait 30 mins for it to propagate.
    - Your app will now be at `https://srsfiapp.com`!

## 📱 Mobile Optimization
This app is built with **Streamlit**, which is **mobile-responsive by default**.
- **On Mobile**: The sidebar collapses into a "hamburger menu" (☰) at the top left.
- **Charts**: All charts use `use_container_width=True`, so they automatically resize to fit your phone screen.
- **Interactivity**: You can pinch-to-zoom on charts and tap buttons just like a native app.
