#!/usr/bin/python

import json
import subprocess


if __name__ == "__main__":


    projects = json.loads( open('projects.json').read() )
    options = json.loads( open('options.json').read() )


    # SHAREDCOUNT API KEY
    APIKEY = str( options['sharedcount']['apikey'] )


    # FETCH SHAREDCOUNT STATS
    for name, project in projects.items() :
        
        domains  = ','.join( map( lambda s: str(s), project['domains'] ) )
        sitemaps = ','.join( map( lambda s: str(s), project['sitemaps'] ) )
        check_https = 'https' in project and project['https'] is True

        stats_cmd = 'python scripts/sharedcount.py'
        stats_cmd += ' --name=' + name
        stats_cmd += ' --sitemap=' + sitemaps
        stats_cmd += ' --domains=' + domains
        if check_https :
            stats_cmd += ' --https'
        stats_cmd += ' --output-dir=output/'
        stats_cmd += ' --apikey=' + APIKEY
        stats_cmd += ' --force'

        project['process'] = subprocess.Popen( stats_cmd, shell=True )


    for name, project in projects.items() :
        project['exit_code'] = project['process'].wait()


    for name, project in projects.items() :

        if project['exit_code'] == 0 :
            print 'ok.'



