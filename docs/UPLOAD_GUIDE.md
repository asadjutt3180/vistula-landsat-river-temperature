# How to publish the code and data (GitHub + Zenodo)

**Where:** code and small data on **GitHub**; a citable, permanent copy with a **DOI** on **Zenodo** (free, operated by CERN, accepted by MDPI). The large whole-river composites (252 MB zipped) go to Zenodo only, because GitHub rejects files larger than 100 MB.

You end up with three links for the paper:
1. GitHub repository (code, small data) – `https://github.com/<USERNAME>/vistula-landsat-river-temperature`
2. Zenodo DOI of the GitHub release – `10.5281/zenodo.XXXXXXX`
3. Zenodo DOI of the large dataset – `10.5281/zenodo.YYYYYYY`

---

## Part A – GitHub (about 10 minutes)

1. Create a free account at https://github.com (use your academic e-mail).
2. Click **+ → New repository**. Name: `vistula-landsat-river-temperature`. Choose **Public**. Do **not** tick "Add a README" (the folder already has one). Click **Create repository**.
3. Upload the folder – choose **one** of the options below.

### Option 1 – GitHub Desktop (easiest, no commands)
1. Install GitHub Desktop from https://desktop.github.com and sign in.
2. **File → Add local repository →** select `E:\Vistula river\GITHUB\vistula-landsat-river-temperature` → it offers to "create a repository" → **Create repository**.
3. Write a summary such as `Initial release for Water manuscript` → **Commit to main**.
4. Click **Publish repository**, untick "Keep this code private", **Publish**.

### Option 2 – command line (Git is already installed on this computer)
Open *Git Bash* in the folder and run, replacing `<USERNAME>`:
```bash
cd "/e/Vistula river/GITHUB/vistula-landsat-river-temperature"
git init
git add .
git commit -m "Initial release for Water manuscript"
git branch -M main
git remote add origin https://github.com/<USERNAME>/vistula-landsat-river-temperature.git
git push -u origin main
```
The first push opens a browser window to sign in to GitHub.

### Option 3 – web upload
On the empty repository page choose **uploading an existing file** and drag the *contents* of the folder (not the folder itself). Works because every file is below 25 MB; the hidden files `.gitignore` and `.zenodo.json` may need to be dragged separately (enable "show hidden files" in Explorer).

After uploading, replace `<USERNAME>` in `README.md` and `CITATION.cff` with your GitHub user name (edit on GitHub with the pencil icon).

---

## Part B – Zenodo DOI for the code (automatic from GitHub)

1. Go to https://zenodo.org → **Log in with GitHub** → authorize.
2. Open **your profile → GitHub** (https://zenodo.org/account/settings/github/) and switch the toggle **ON** for `vistula-landsat-river-temperature`.
3. On GitHub, open the repository → **Releases → Create a new release** → tag `v1.0.0`, title `v1.0.0 – code and data for the Water article` → **Publish release**.
4. Within a few minutes Zenodo archives the release and shows a DOI (`10.5281/zenodo.XXXXXXX`). Zenodo reads the metadata from `.zenodo.json`. Copy the DOI badge into `README.md` if you wish.

## Part C – Zenodo record for the large dataset

1. On https://zenodo.org click **New upload**.
2. Drag in the four files from `E:\Vistula river\GITHUB\zenodo_upload\` (two ZIP files and their `.sha256` files).
3. Metadata:
   * Resource type: **Dataset**
   * Title: *Monthly Landsat surface temperature along the Vistula River centreline, May–November 2000–2024*
   * Creators: the four authors (add ORCID iDs if you have them)
   * Description: paste the text from `docs/zenodo_dataset_description.md`
   * Licence: **Creative Commons Attribution 4.0**
   * Related works: "Is supplement to" → the GitHub/Zenodo DOI of Part B (and later the article DOI)
4. Click **Get a DOI now!** (reserves the DOI before publishing – you can put it into the manuscript immediately), then **Publish**.

## Part D – after the article is accepted
Add the article DOI (`10.3390/w…`) to both Zenodo records (**Edit → Related works**) and to `CITATION.cff`, then publish a new GitHub release (`v1.0.1`) – Zenodo creates a new version under the same concept DOI.

## Private during review?
Both GitHub and Zenodo can be public now (recommended by MDPI). If you prefer to wait, keep the GitHub repository private and use Zenodo's **reserved DOI** in the manuscript; publish both at acceptance.
