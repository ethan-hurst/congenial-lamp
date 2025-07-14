# Running CodeForge on Replit

This guide will help you deploy CodeForge on Replit.

## Prerequisites

1. A Replit account
2. Fork or import this repository to your Replit account
3. Optional: GitHub OAuth app credentials for social login
4. Optional: OpenAI API key for AI features

## Quick Start

1. **Import to Replit**
   - Go to [Replit](https://replit.com)
   - Click "Create Repl"
   - Choose "Import from GitHub"
   - Enter this repository URL

2. **Run the Application**
   - Once imported, Replit should automatically detect the `.replit` configuration
   - Click the "Run" button
   - The startup script will:
     - Install all dependencies
     - Set up the database
     - Start both backend and frontend servers

3. **Access the Application**
   - Frontend: `https://[your-repl-name].[your-username].repl.co:3000`
   - Backend API: `https://[your-repl-name].[your-username].repl.co:8000`
   - API Documentation: `https://[your-repl-name].[your-username].repl.co:8000/docs`

4. **Default Login**
   - Email: `admin@codeforge.dev`
   - Password: `admin123`
   - ⚠️ **Important**: Change this password after first login!

## Configuration

### Environment Variables

The startup script automatically creates `.env` files, but you can customize them:

#### Backend (.env in codeforge/backend/)
```env
# Database (Replit provides PostgreSQL)
DATABASE_URL=postgresql://codeforge:codeforge@localhost:5432/codeforge_db

# Add your API keys
OPENAI_API_KEY=your_openai_key_here
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

#### Frontend (.env in codeforge/frontend/)
```env
REACT_APP_API_URL=https://[your-repl].repl.co:8000
REACT_APP_WS_URL=wss://[your-repl].repl.co:8000
REACT_APP_GITHUB_CLIENT_ID=your_github_client_id
```

### Secrets Management

For sensitive data, use Replit Secrets:
1. Click on the "Secrets" tab (lock icon)
2. Add your secrets:
   - `OPENAI_API_KEY`
   - `GITHUB_CLIENT_SECRET`
   - `JWT_SECRET_KEY`
   - `EMAIL_PASSWORD`

## Features Available on Replit

✅ **Fully Functional**
- User authentication and management
- Project creation and management
- Database provisioning and branching
- AI-powered code generation
- Infrastructure management
- Real-time collaboration
- Code editor integration

⚠️ **Limited Functionality**
- Docker-based sandboxing (Replit doesn't support Docker)
  - Falls back to process-based isolation
- Some advanced infrastructure features may be limited

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL status
pg_ctl status

# Restart PostgreSQL
pg_ctl restart
```

### Port Conflicts
- Make sure ports 3000 and 8000 are not used by other services
- Check the "Ports" tab in Replit to see exposed ports

### Performance
- Replit free tier has limited resources
- Consider upgrading to Replit Core for better performance
- Enable production mode by setting `DEBUG=False` in backend .env

### Persistent Storage
- Replit provides persistent storage for databases
- Uploaded files are stored in the filesystem
- Regular backups are recommended

## Deployment to Production

From Replit, you can deploy to:
1. **Replit Deployments** (Recommended)
   - Click "Deploy" button
   - Choose deployment type
   - Follow the wizard

2. **External Hosting**
   - Export your code
   - Deploy backend to services like Heroku, Railway, or Render
   - Deploy frontend to Vercel, Netlify, or Cloudflare Pages
   - Use managed PostgreSQL from Supabase, Neon, or Railway

## Support

- Check the logs in the Console tab
- Backend logs: Look for FastAPI/Uvicorn output
- Frontend logs: Look for React/npm output
- Database logs: Check PostgreSQL output

## Security Notes

1. **Change default passwords immediately**
2. **Use Replit Secrets for sensitive data**
3. **Enable HTTPS in production**
4. **Configure CORS properly for your domain**
5. **Regularly update dependencies**

---

Happy coding with CodeForge on Replit! 🚀