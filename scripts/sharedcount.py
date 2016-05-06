#!/usr/bin/python

import sys, os, getopt, csv, datetime, errno
from datetime import timedelta
import xml.dom.minidom as minidom
import urllib, urllib2, socket
import json, re, string
from urlparse import urlparse





def fetch_sitemap_url( url, domains, limit, i=0 ) :

    print url + '...'

    urls = {}

    xml = urllib2.urlopen( url )
    sitemap = minidom.parse(xml)
    links = sitemap.getElementsByTagName("loc")

    for link in links :

        if limit is None or i < limit :
            i += 1

            url = str( link.firstChild.data )

            if url.endswith('.xml') :
                urls.update( fetch_sitemap_url(url, domains, limit, i) )

            else :
                u = urlparse(url)
                page = u.path + u.params + u.query;
                scheme = u.scheme

                urls[ page ] = []

                for domain in domains :

                    url_variant = scheme+'://'+domain+page
                    urls[ page ].append( url_variant )

                    if scheme is not 'https' and check_https :
                        ssl_variant = 'https://'+domain+page
                        urls[ page ].append( ssl_variant )

    return urls




def get_urls_list( sitemaps, domains, limit ) :
    urls = {}
    for sitemap_url in sitemaps :
        urls.update( fetch_sitemap_url(sitemap_url, domains, limit) )
    return urls




def check_args(argv) :

    global project_name, sitemaps, domains, limit, output_dir, apikey, force, yesterday, check_https

    def usage_and_die() : 
        print 'sharedcount.py --name=project_name --apikey=xxxxx --domains=foo.be,www.foo.be,mirror.foo.fr --sitemap=sitemap_url[,sitemap2.url] [--output-dir=dirname] [--force] [--limit=n] [--yesterday]'
        sys.exit( errno.EINVAL )

    try:
        opts, args = getopt.getopt( argv, "c:n:d:s:o:l:k:", ["name=", "apikey=", "domains=", "sitemap=", "output-dir=", "limit=", "force", "yesterday", "https"] )
    except getopt.GetoptError as err:
        sys.stderr.write( str(err)+'\n' )
        usage_and_die()

    for opt, arg in opts:
        if opt  in ("-h", "--help"):
            usage_and_die()
        elif opt in ("-n", "--name") :
            project_name = arg
        elif opt in ("-k", "--apikey") :
            apikey = arg
        elif opt in ("-d", "--domains") :
            domains = string.split(arg, ',')
        elif opt in ("-s", "--sitemap") :
            sitemaps = string.split(arg, ',')
        elif opt in ("-o", "--output-dir") :
            output_dir = arg.strip('/')
        elif opt in ("-l", "--limit") :
            limit = int(arg)
        elif opt == '--force' : 
            force = True
        elif opt == '--yesterday' : 
            yesterday = True
        elif opt == '--https' : 
            check_https = True

    if sitemaps is [] or domains is [] or project_name is None or apikey is None :
        usage_and_die()




def get_csv(create=True) :

    global output_dir, project_name, metrics

    folder = output_dir+'/'+project_name
    if not os.path.exists( folder ) :
        os.makedirs( folder )

    csv_file = folder+'/'+project_name+'.csv'

    if create and not os.path.isfile( csv_file ) :
        print 'Create ' + csv_file + '...'

        writer = csv.writer( open(csv_file, 'wb') )
        writer.writerow( ['Date', 'Page'] + metrics )

    return csv_file




def csv_needs_update() :

    csv_file = get_csv()
    tmp_file = 'tmp_'+project_name+'.csv'

    reader = csv.reader( open(csv_file, 'rb'), delimiter=',' )
    next(reader, None) # skip header

    last_date = None
    for row in reader :
        last_date = row[0]

    needs_update = last_date is None or datetime.date.today() > datetime.datetime.strptime(last_date, "%d/%m/%y").date()


    if not needs_update and force :

        # remove today's entries in csv
        reader = csv.reader( open(get_csv(), 'rb'), delimiter=',' )
        writer = csv.writer( open(tmp_file, 'wb') )
        for row in reader :
            if ( row[0] != last_date ) :
                writer.writerow( row )
        os.rename( tmp_file, get_csv(False) )

        needs_update = True


    return needs_update




def get_cumulative_stats() :

    previous = {}

    reader = csv.reader( open(get_csv(), 'rb'), delimiter=',' )
    next(reader, None) # skip header

    for row in reader :
        page = row[1]
        stats = map(int, row[2:])
        if previous.has_key( page ) :
            previous[page] = [ sum(x) for x in zip(previous[page], stats) ]
        else :
            previous[page] = stats

    return previous





def get_quota() :
    global apikey 

    req = "http://plus.sharedcount.com/quota?apikey="+apikey
    stream = urllib2.urlopen( req )
    data = json.load( stream )
    
    used = data['quota_used_today']
    remaining = data['quota_remaining_today']
    return used, remaining
    

import time
from functools import wraps



def retry( ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None ):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 0:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck, e:
                    print "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
                    lastException = e
            raise lastException
        return f_retry
    return deco_retry



def fetch_sharedcount_data( urls ) :

    global result, apikey

    @retry( urllib2.URLError, tries=3, delay=5, backoff=1.5 )
    def urlopen_with_retry( url ) :
        return urllib2.urlopen( url, timeout=60 )


    def sharedcount_data( url ) :
        print url
        req = "http://plus.sharedcount.com/?url="+url+"&apikey="+apikey
        
        try :
            stream = urlopen_with_retry( req )
            data = json.load( stream )
            return data

        except urllib2.URLError as e:
            print '!!!!!! URL error !'
            return False

        except socket.timeout as e:
            print '!!!!!! Timeout error !'
            return False

        

    for page, variants in urls.items() :
        for variant in variants :
            data = sharedcount_data( variant )
            if data :
                result[page]['FB comments']     += int( data['Facebook']['comment_count'] )
                result[page]['FB likes']        += int( data['Facebook']['like_count'] )
                result[page]['FB shares']       += int( data['Facebook']['share_count'] )
                result[page]['Tweets']          += int( data['Twitter'] )
                result[page]['Google+ shares']  += int( data['GooglePlusOne'] )
                result[page]['Linkedin shares'] += int( data['LinkedIn'] )
                result[page]['Pinterest pins']  += int( data['Pinterest'] )



def main(argv) :

    global domains, sitemaps, project_name, limit, output_dir, result, metrics, yesterday

    
    # CHECK PARAMETERS
    check_args( argv )


    today = datetime.date.today().strftime("%d/%m/%y")
    if yesterday :
        today = ( datetime.date.today() - timedelta(days=1) ).strftime("%d/%m/%y")


    # DO WE NEED AN UPDATE ?
    if not csv_needs_update() :
        print 'CSV file is up to date, abort.'
        sys.exit( errno.EPERM )

    
    # CALCULATE CUMULATIVE PREVIOUS RESULTS
    previous = get_cumulative_stats()


    # GET URLS FROM SITEMAP
    print 'Fetching sitemaps...' 
    urls = get_urls_list( sitemaps, domains, limit )
    print str(len(urls)) + ' links found.'


    # CHECK WE HAVE ENOUGH QUOTA FOR TODAY
    used, remaining = get_quota()
    if remaining < len(urls) :
        sys.stderr.write( 'Remaining quota ('+str(remaining)+') too small for request ('+str(len(urls))+' urls), exit.\n' )
        sys.exit( errno.EDQUOT )


    # INIT RESULTS
    for page in urls.keys() :
        stats = [0] * len(metrics)
        if ( previous.has_key(page) ) :
            stats = previous.get(page) 
            stats = map( lambda k : -int(k), stats )
        result[page] = dict( zip( metrics, stats ) )


    # FETCH TODAY RESULTS
    print '\nFetching sharedcount results for '+str(len(urls))+' urls...' 
    fetch_sharedcount_data( urls )

    
    # APPEND TODAY RESULTS TO CSV
    print 'Updating CSV file...'
    f = open( get_csv(), 'ab' )
    writer = csv.writer(f)

    for page, data in result.items() :
        row = [ today, page ] # date, page
        for metric in metrics :
            row.append( data[metric] ) 
        writer.writerow( row )
    f.close()



    # DISPLAY REMAINING QUOTA
    used, remaining = get_quota()
    print 'Finished, '+str(used)+' quota used today, '+str(remaining)+' quota remaining for today.'




if __name__ == "__main__":
    
    limit = None
    force = False
    yesterday = False
    check_https = False
    sitemaps = []
    project_name = None
    domains = []
    output_dir = '.'
    apikey = None
    result = {}
    metrics = ['FB likes', 'FB shares', 'FB comments', 'Tweets', 'Google+ shares', 'Linkedin shares', 'Pinterest pins' ]

    main( sys.argv[1:] )

