# Deploy Mac to Google Cloud on free resources

Backend on **Cloud Run** (scales to zero), frontend on **Firebase Hosting** (free Spark quota).
Run every command from the repository root on your own machine.

> Free tiers cover a low-traffic demo. Gemini usage is billed separately by Google; use the free Gemini key only with made-up test data, never real customer data. Servicing data is SQLite inside the container and resets when the container restarts, which is fine for a demo with the sample data.

## 0. One-time setup on your machine

- Install the Google Cloud CLI: https://cloud.google.com/sdk/docs/install
- Install Node.js, then the Firebase CLI: `npm install -g firebase-tools`
- Have a Gemini API key from Google AI Studio.

```bash
gcloud auth login
firebase login
```

## 1. Create the project and turn on billing

Cloud Run needs a billing account even when you stay inside the free tier.

```bash
export PROJECT_ID=mac-mortgage-advisor-<something-unique>
export REGION=us-central1
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID
gcloud billing accounts list
gcloud billing projects link $PROJECT_ID --billing-account=<BILLING_ACCOUNT_ID>
```

Set a budget alert (for example $5) in the console: **Billing → Budgets & alerts → Create budget**. It emails you; it does not stop spending.

## 2. Enable the APIs

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com
```

## 3. Store the Gemini key in Secret Manager

```bash
printf '%s' 'YOUR_GEMINI_API_KEY' | gcloud secrets create gemini-api-key --data-file=-
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor
```

## 4. Deploy the backend to Cloud Run

`ALLOWED_ORIGINS` lists the Firebase addresses the frontend will have (step 6), so only your frontend can open calls. The `^@^` tells gcloud to split variables on `@` because the value contains commas.

```bash
gcloud run deploy mortgage-advisor --source . --region $REGION \
  --allow-unauthenticated \
  --min-instances 0 --max-instances 2 \
  --cpu 1 --memory 512Mi \
  --timeout 3600 --concurrency 20 --session-affinity \
  --set-secrets GOOGLE_API_KEY=gemini-api-key:latest \
  --set-env-vars "^@^GOOGLE_GENAI_USE_VERTEXAI=FALSE@ALLOWED_ORIGINS=https://${PROJECT_ID}.web.app,https://${PROJECT_ID}.firebaseapp.com"
```

- Answer **Y** when asked to create an Artifact Registry repository.
- If the build fails with a permissions error, grant the build role and run the deploy again:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role=roles/cloudbuild.builds.builder
```

Check it:

```bash
export BACKEND_URL=$(gcloud run services describe mortgage-advisor --region $REGION --format='value(status.url)')
curl $BACKEND_URL/healthz
```

You should see `{"ok":true,...}`. Opening `$BACKEND_URL` in a browser also works: the container serves the frontend too.

## 5. Point the frontend at the backend

Edit `src/frontend/config.js` and paste the URL from step 4:

```js
window.MAC_CONFIG = {
  backendUrl: "https://mortgage-advisor-xxxxxxxxxx-uc.a.run.app",
};
```

## 6. Deploy the frontend to Firebase Hosting

```bash
firebase projects:addfirebase $PROJECT_ID
firebase deploy --only hosting --project $PROJECT_ID
```

The output shows the **Hosting URL**, normally `https://<PROJECT_ID>.web.app`. If it is different, update `ALLOWED_ORIGINS`:

```bash
gcloud run services update mortgage-advisor --region $REGION \
  --update-env-vars "^@^ALLOWED_ORIGINS=https://<your-site>.web.app,https://<your-site>.firebaseapp.com"
```

## 7. Test

Open the Hosting URL, press **Call Mac**, allow the microphone, and try the reference call:
"I have a couple of properties in Texas and want a HELOC of about $40,000 on the one I rent out."

The first call after a quiet period takes a few seconds to connect while Cloud Run starts the container.

## Redeploying

```bash
gcloud run deploy mortgage-advisor --source . --region $REGION   # backend; keeps the settings above
firebase deploy --only hosting --project $PROJECT_ID              # frontend
```

## Staying inside the free tier

| Item | Free allowance (check current limits) | Watch out for |
|---|---|---|
| Cloud Run | 2M requests, 180,000 vCPU-s, 360,000 GiB-s per month | `--min-instances 1` keeps an instance running and goes past it |
| Cloud Build | Free build minutes each month | Many redeploys in a month |
| Artifact Registry | 0.5 GB storage | Each deploy adds an image; delete old ones in the console |
| Secret Manager | 6 secret versions, 10,000 accesses | — |
| Firebase Hosting | ~10 GB storage, ~360 MB/day transfer | — |
| Gemini API | Free tier with rate limits | Free-tier data may be used by Google; test data only |

## Troubleshooting

| Symptom | Fix |
|---|---|
| Page loads, call never connects | `backendUrl` in `config.js` is wrong, or `ALLOWED_ORIGINS` doesn't match the Hosting URL (Cloud Run logs show `rejected /ws from origin`) |
| Call drops after 5 minutes | Deploy with `--timeout 3600` |
| "Gemini API key was rejected" | Check the secret value and that the service account can read it (step 3) |
| Logs | `gcloud run services logs read mortgage-advisor --region $REGION` |
