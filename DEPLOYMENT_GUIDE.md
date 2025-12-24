# Deployment Guide for Family Expense Tracker

This guide will help you deploy the Family Expense Tracker application on Vercel, which offers free hosting and allows the app to run continuously without requiring your PC to be on.

## Prerequisites

1. A [Vercel](https://vercel.com/) account (free tier)
2. A [GitHub](https://github.com/) account
3. (Optional) A PostgreSQL database for production use

## Step 1: Push Your Code to GitHub

1. Create a new repository on GitHub
2. Initialize git in your project folder:
   ```
   git init
   ```
3. Add all your files:
   ```
   git add .
   ```
4. Commit your files:
   ```
   git commit -m "Initial commit"
   ```
5. Link your local repository to GitHub and push:
   ```
   git remote add origin https://github.com/yourusername/your-repo-name.git
   git push -u origin main
   ```

## Step 2: Set Up Vercel

1. Sign up or log in to [Vercel](https://vercel.com/)
2. Click "Add New Project"
3. Choose the repository you pushed to GitHub
4. Vercel will automatically detect that this is a Python project
5. Configure the following settings:
   - Framework Preset: Choose "Other"
   - Root Directory: Leave as is (default: `/`)
   - Build Command: Leave empty
   - Output Directory: Leave empty
   - Install Command: Leave as is (default will use your vercel-requirements.txt)

## Step 3: Configure Environment Variables

Add the following environment variables in the Vercel project settings:

1. `SESSION_SECRET` - A secure random string for Flask session encryption
2. `DATABASE_URL` (optional) - If you have a PostgreSQL database, add the connection string here
3. Add any other API keys or secrets your app uses

## Step 4: Deploy

1. Click "Deploy" in the Vercel interface
2. Wait for the build and deployment to complete (usually takes 1-2 minutes)
3. Vercel will provide a deployment URL like `https://your-project-name.vercel.app`

## Step 5: Set Up a Database (Optional)

For proper persistence, you should set up a PostgreSQL database. Several providers offer free tiers:

1. [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres) (limited free usage)
2. [Supabase](https://supabase.com/) (free tier with generous limits)
3. [Neon](https://neon.tech/) (free tier available)

After setting up the database:
1. Get the connection URL from your database provider
2. Add it as `DATABASE_URL` in your Vercel project environment variables
3. Redeploy your application

## Maintaining Your Application

### Making Updates

When you want to update your application:

1. Make changes to your local code
2. Commit and push to GitHub:
   ```
   git add .
   git commit -m "Description of your changes"
   git push
   ```
3. Vercel will automatically deploy the new version

### Monitoring

Vercel provides basic monitoring tools in the dashboard:
- Deployment status
- Build logs
- Function invocations
- Basic analytics

## Limitations of Free Tier

The free tier of Vercel has some limitations:
- Serverless function execution time limit (10 seconds)
- Limited build minutes per month
- Limited bandwidth

For a simple expense tracker application, these limitations should not be an issue for normal family use.

## Troubleshooting

If your deployment fails:

1. Check the build logs in the Vercel dashboard
2. Ensure all required dependencies are in vercel-requirements.txt
3. Verify that your environment variables are correctly set

## Other Deployment Options

If Vercel doesn't suit your needs, here are alternatives:

1. [Render](https://render.com/) - Similar to Vercel with a free tier
2. [Railway](https://railway.app/) - Easy deployment with a generous free tier
3. [Fly.io](https://fly.io/) - Small VMs close to users with a free tier
4. [PythonAnywhere](https://www.pythonanywhere.com/) - Python-specific hosting with a free tier