
# Installation

```sh
$ mv options.json.example options.json
# Enter your Sharedcount API key
```

# Usage


## Manually

Create CSV for today :
```sh
$ python scripts/sharecount.py --apikey=xxxx --sitemap=http://website.com/fr/sitemap.xml,http://website.com/en/sitemap.xml --domains=website.com,www.website.com --name=website-name --output-dir=output/  
```


## Projects presets

```sh
$ mv projects.json.example projects.json
# Enter here all the projects options
```

Runs the script for projects listed in `projets.json` :
```sh
$ python ./do_it.py
```
This fetches social data and uploads it to tableau, according to the options listed in `options.json`.


## Cron schedule

Schedule automatic fetch each day at 23:30 :

```sh
$ crontab -e
```

```sh
MAILTO=xxx@xxx.com
30 23 * * *   cd /path/to/app ; python do_it.py
```