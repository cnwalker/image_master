import os, sys
import urllib
import urllib2
import concurrent.futures

import requests

BING_ROOT_URL = 'https://api.cognitive.microsoft.com/bing/v5.0/images/search'
BING_IMAGE_API_KEY = '19aa2d868e5843c1951325a135db5703' # cnwalker
GOOGLE_IMAGE_API_KEY = '' # cnwalker

# /Users/jsalavon/Documents/ml/data/'
IMAGE_DOWNLOAD_DIR = '%s/' % os.path.dirname(os.path.realpath(__file__))

def padFront(num, desired_length, val=0):
    # Returns a zero padded string with the length equal to desired_length
    # num should be in the form of a string (i.e '12', '15')
    return ("0" * max(desired_length - len(num), 0)) + num

def cleanURL(urlObj):
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
        error_messages = '\n'.join(map(getMessage, response.json().get('errors')))
        print 'ERROR FROM SERVER:\n' + error_messages + '\n--------------'
        raise

def getImageURLs(query, offset, count, adult_filter='Off'):
    if int(count) == 0:
        raise ValueError("count must be greater than 0")

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
        imageURLs = map(cleanURL, bing_response['value'])
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
                    print('Downloaded image %d of %d' % (i, numImages - 1))
                except Exception as e:
                    print('%r generated an exception: %s' % (url, exc))
    return None

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print('Not enough parameters!\n Usage: python image_master.py \
        <query> <offset> <count> <adult - String, Moderate, Off>')
    else:
        query, offset, count, adult_filter = sys.argv[1:]
        imageURLs = getImageURLs(query, offset, count, adult_filter)
        downloadImages(imageURLs, query, offset, count)
