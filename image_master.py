import os, sys
import urllib
import urllib2
import concurrent.futures

import requests

# Bing configs
BING_ROOT_URL = 'https://api.cognitive.microsoft.com/bing/v5.0/images/search'
BING_IMAGE_API_KEY = '19aa2d868e5843c1951325a135db5703' # cnwalker

# Google configs
GOOGLE_ROOT_URL = 'https://www.googleapis.com/customsearch/v1'
GOOGLE_CX_KEY = '014703581600628456418:bikvjo-7psc' #cnwalker
GOOGLE_IMAGE_API_KEY = 'AIzaSyAi70PTj2pyYZkK23WfuXbezshP9iBRk6g' #AIzaSyBDzxv_1DTFpMrLObHVyzZ7xU7eo1PX0eg # cnwalker

IMAGE_DOWNLOAD_DIR = '%s/' % os.path.dirname(os.path.realpath(__file__))

def padFront(num, desired_length, val=0):
    # Returns a zero padded string with the length equal to desired_length
    # num should be in the form of a string (i.e '12', '15')
    return ("0" * max(desired_length - len(num), 0)) + num

def cleanBingURL(urlObj):
    # Quotes reserved characters and returns a tuple of the URL
    # and the target image's file extension
    formatted_url = urllib2.quote(urlObj['contentUrl'].encode('utf-8'), safe="%/:=&?~#+!$,;'@()*[]")
    file_extension = urlObj.get('encodingFormat')
    return (formatted_url, file_extension)

def checkResponseForErrors(response):
    # Raises an error with the response from the server for a 4xx or 5xx error
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        getMessage = lambda x: x.get('message')
        error_messages = '\n'.join(map(getMessage, response.json().get('error').get('errors')))
        print 'ERROR FROM SERVER:\n' + error_messages + '\n--------------'
        raise

def assertPositiveCount(count):
    if count <= 0:
        raise ValueError("count must be greater than 0")


def getBingImageURLs(query, offset, count, adult_filter='Off'):
    assertPositiveCount(count)

    # First get the image urls from Bing
    response = requests.post(BING_ROOT_URL,
        # Enter POST parameters in this dictionary
        params={
            'q': query,
    		'count': count,
    		'offset': offset,
    		'safesearch': adult_filter
        },
        headers={'Ocp-Apim-Subscription-Key': BING_IMAGE_API_KEY})

    checkResponseForErrors(response)

    if response.ok:
        bing_response = response.json()
        # We need to clean up the image urls so we can download them
        imageURLs = map(cleanBingURL, bing_response['value'])
        return imageURLs

    return None

def downloadImages(imageURLs, query, offset, count, max_threads=4):
    numImages = len(imageURLs)
    maxPadding = len(str(numImages))
    # Download directory is of form <query>_<count>_<offset>
    query_dir = '%s_%s_%s/' % (query, offset, count)
    download_dir = IMAGE_DOWNLOAD_DIR + query_dir

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # For a two core machine, more than 4 threads is probably going to be
    # slower than 4 b/c of context switching overhead
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        all_jobs = {}
        for i in xrange(numImages):
            print "image num: %d" % (int(offset) + i)
            file_extension = imageURLs[i][1]
            download_path = (
                download_dir +
                padFront(str(i), maxPadding) +
                '_' + query + '.' + file_extension
            )

            # Submit a job to the thread pool to download the images
            image_download_job = executor.submit(urllib.urlretrieve,
            imageURLs[i][0], download_path)

            # The jobs are keys so they can be parsed by as_completed
            # saving the URLs so we can print the URL if there is an
            # error downloading one
            all_jobs[image_download_job] = imageURLs[i][0]

            for future in concurrent.futures.as_completed(all_jobs):
                url = all_jobs[future]
                try:
                    data = future.result()
                except Exception as e:
                    print('%r generated an exception: %s' % (url, e))
    return None

def getGoogleImageURLs(query, offset, count, adult_filter='off'):
    imageURLs = []
    count = int(count)
    assertPositiveCount(count)
    # Add an iteration if there is leftover, otherwise do not
    num_iterations = count/10 + int(not(not(count % 10)))
    offset = int(offset)
    if offset == 0:
        offset += 1
    initial_offset = offset
    initial_count = count

    for i in xrange(num_iterations):
        print min(count, 10)
        # First get the image urls from Google
        response = requests.get(GOOGLE_ROOT_URL,
            params={
                'q': query,
                'cx': GOOGLE_CX_KEY,
                'key': GOOGLE_IMAGE_API_KEY,
                'safe': adult_filter.lower(),
                'start': offset + (i * 10),
                'num': min(count, 10),
                'searchType': 'image',
                'type': 'application/json'
            })

        checkResponseForErrors(response)

        if response.ok:
            google_response = response.json()
            imageURLs += map(lambda x: (x.get('link'), x.get('link').split('.')[-1]),
                            google_response['items'])
            print "batch: %d" % num_iterations
            downloadImages(imageURLs, query, initial_offset, initial_count)
            count -= 10

    if len(imageURLs):
        return imageURLs
    return None


search_engine_table = {
    'google': getGoogleImageURLs,
    'bing': getBingImageURLs
}

if __name__ == "__main__":
    num_args = len(sys.argv)
    if num_args < 5:
        print('Not enough parameters!\n Usage: python image_master.py \
        <query> <offset> <count> <adult - String, Moderate, Off> <(optional) engine - bing, google>')
    else:
        query, offset, count, adult_filter = sys.argv[1:5]
        search_function = search_engine_table['google'] # default to google
        if num_args == 6:
            search_function = search_engine_table.get(sys.argv[-1])
        if (search_function == None):
            raise ValueError("Invalid search engine! Only bing and google (lowercase) are currently supported")

        imageURLs = search_function(query, offset, count, adult_filter)

        if sys.argv[-1].lower() == 'bing':
            downloadImages(imageURLs, query, offset, count)
