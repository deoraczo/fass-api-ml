from redis import Redis
import json
import numpy as np
import base64

stream_key = 'tickets'
hostmane = 'localhost'
port = 6379
group = 'reader'

def connect_to_redis():
    r = Redis(hostmane, port, retry_on_timeout=True)
    return r


def handler(val):
    # Conversion: base-64 string --> array of bytes --> array of integers
    base64string = val['pix'] #pix is base-64 encoded string
    byteArray = base64.b64decode(base64string) #byteArray is an array of bytes
    npArray = np.frombuffer(byteArray, np.uint8) #npArray is an array of integers

    # Reshape array into an RGB image matrix of shape (channels, rows, cols)
    rows = val['rows']
    cols = val['cols']
    print(rows, cols)
    imgR = npArray[0::4].reshape((rows, cols))
    imgG = npArray[1::4].reshape((rows, cols))
    imgB = npArray[2::4].reshape((rows, cols))
    img = np.stack((imgR, imgG, imgB))
    img = np.moveaxis(img, 0, -1)

    return img

def get_data(redis_connection: Redis):
    last_id = 0
    sleep_ms = 5000
    redis_connection.xgroup_create(stream_key , group)
    while True:
        try:
            streams = redis_connection.xreadgroup(group, "lslslsl", {stream_key: ">"}, count=1, block=0)
            # print(streams)
            for stream in streams:
                key, value = stream
                id, data = value[0]
                data_dict = {k.decode("utf-8"): data[k].decode("utf-8") for k in data}
             
                d = json.loads(data_dict['data'])
                # other = {data_dict['data'][k]: k for k in data_dict['data']}
                # print(d['pix'])
                img = handler(d)
                print(img)
            # resp = redis_connection.xread(
            #     {stream_key: last_id}, count=1, block=sleep_ms
            # )
            # if resp:
            #     key, messages = resp[0]
            #     print(messages)
            #     last_id, data = messages[0]
            #     data_dict = {k.decode("utf-8"): data[k].decode("utf-8") for k in data}
            #     # print("REDIS ID: ", last_id)
            #     print("      --> ", data_dict['data'])

        except ConnectionError as e:
            print("ERROR REDIS CONNECTION: {}".format(e))

if __name__ == "__main__":
    connection = connect_to_redis()
    get_data(connection)