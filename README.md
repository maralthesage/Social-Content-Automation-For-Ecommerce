# Social Media Automation

**Social Media Content Generation and Posting Automation** is a Python-based automation tool that streamlines the process of posting content across multiple social media platforms. By leveraging platform-specific APIs, opensource LLMs using Ollama (and here, for our purposes: qwen3 model) to generate and optimize text contents (captions, descriptions, etc.), it enables users to schedule and publish posts efficiently, reducing manual effort and ensuring consistent online presence.

## 🚀 Features

* **Multi-Platform Support**: Automatically post content to various social media platforms such as Facebook, Twitter, LinkedIn, and Instagram.
* **Scheduled Posting**: Plan and schedule posts to be published at optimal times for maximum engagement.
* **Content Management**: Organize and manage your content, including text, images, and links, within a centralized system.
* **Logging and Monitoring**: Keep track of posting activities with detailed logs for auditing and troubleshooting.

## 🛠️ Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/maralthesage/social_auto_post.git
   cd social_auto_post
   ```



2. **Create a Virtual Environment** (Optional but recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```



3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```



## ⚙️ Configuration

1. **API Credentials**:

   Obtain API credentials for each social media platform you intend to use. This typically involves creating developer accounts and registering applications to receive API keys and tokens.

2. **Environment Variables**:

   Create a `.env` file in the project root directory and add your API credentials:

   ```ini
   FACEBOOK_API_KEY=your_facebook_api_key
   TWITTER_API_KEY=your_twitter_api_key
   LINKEDIN_API_KEY=your_linkedin_api_key
   INSTAGRAM_API_KEY=your_instagram_api_key
   ```



Ensure that this file is included in your `.gitignore` to prevent sensitive information from being committed to version control.

## 📈 Usage

1. **Prepare Your Content**:

   Organize your content (text, images, links) in a structured format, such as a CSV file or a database, depending on your implementation.

2. **Run the Scripts**:

   Execute the run_daily script to initiate the post creatin process, and then post_prepared_content.py to post on social media. Or rather, use a cron job or a task scheduler to create posts daily. For our purpose, it is important that the posts are created on a daily basis, based on the inventory stock update. This can be changed for posts or services that are not inventory dependent.

   ```bash
   python run_daily.py
   python post_prepared_content.py
   ```



The script will read your content, authenticate with each configured social media platform, and publish the posts according to your schedule.

## 🧪 Testing

Before deploying the tool in a production environment, conduct thorough testing:

* **Dry Runs**: Use test accounts or sandbox environments provided by social media platforms to verify functionality without affecting live accounts.
* **Error Handling**: Ensure that the script gracefully handles API errors, rate limits, and network issues.
* **Logging**: Review logs to confirm that posts are being published as expected.



---

*Note: Replace placeholder values such as `your_facebook_api_key` and `your-email@example.com` with your actual API credentials and contact information.*

