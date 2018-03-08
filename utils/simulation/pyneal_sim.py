"""
Tool to simulate the output results server of Pyneal. This tool will simulate the
results server from  Pyneal as well as populate it with fake
data at a rate of one new volume per TR (user can specify TR below)

Once running, the resultsServer will listen for requests over the specified
socket and return a response.

** Message formats *********************
Incoming requests from clients should be 4-character strings representing the
requested volume number (zero padding to make 4-characters). E.g. '0001'

Responses from the server will be JSON strings:
    If the results from the requested volume exist:
        e.g. {'foundResults': True, 'average':2432}
    If they don't:
        {'foundResults': False}
"""
import sys
import os
from os.path import join
import json
import atexit
import socket
from threading import Thread
from pathlib import Path
import time

import numpy as np


class ResultsServer(Thread):
    """
    Class to serve results from real-time analysis. This server will accept
    connections from remote clients, check if the requested results are available,
    and return a JSON-formatted message

    Input a dictionary called 'settings' that has (at least) the following keys:
        resultsServerPort: port # for results server socket [e.g. 5555]
    """

    def __init__(self, settings):
        # start the thread upon creation
        Thread.__init__(self)

        # configuration parameters
        self.alive = True
        self.results = {}       # store results in dict like {'vol#':{results}}
        self.host = '127.0.0.1'
        self.resultsServerPort = settings['resultsServerPort']
        self.maxClients = 1

        # launch server
        self.resultsSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.resultsSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.resultsSocket.bind((self.host, self.resultsServerPort))
        self.resultsSocket.listen(self.maxClients)
        print('Results Server bound to {}:{}'.format(self.host, self.resultsServerPort))
        print('Results Server alive and listening....')

        # atexit function, shut down server
        atexit.register(self.killServer)


    def run(self):
        """
        Run server, listening for requests and returning responses to clients
        """
        while self.alive:
            ### Listen for new connections, redirect clients to new socket
            connection, address = self.resultsSocket.accept()
            print('Results server received connection from: {}'.format(address))

            ### Get the requested volume (should be a 4-char string representing
            # volume number, e.g. '0001')
            recvMsg = connection.recv(4).decode()
            print('Received request: {}'.format(recvMsg))

            # reformat the requested volume to remove any leading 0s
            requestedVol = str(int(recvMsg))

            ### Look up the results for the requested volume
            volResults = self.requestLookup(requestedVol)

            ### Send the results to the client
            self.sendResults(connection, volResults)
            print('Response: {}'.format(volResults))

            # close client connection
            connection.close()


    def updateResults(self, volIdx, volResults):
        """
        Add the supplied result to the results dictionary.
            - vol: the volume number associated with this result
            - volResults: dictionary containing all of the results for this volume
        """
        self.results[str(volIdx)] = volResults
        print('vol {} - {} added to resultsServer'.format(volIdx, volResults))


    def requestLookup(self, vol):
        """
        Check to see if there are results for the requested volume. Will return a
        dictionary of results for this volume. At a minimum, the dictionary will
        contain an entry with the key 'foundResults' and the value is True or
        False based on whether there are any results for this volume.
        """
        if str(vol) in self.results.keys():
            theseResults = self.results[str(vol)]
            theseResults['foundResults'] = True
        else:
            theseResults = {'foundResults': False}
        return theseResults


    def sendResults(self, connection, results):
        """
        Format the results dict to a json string, and send results to the client.
        Message will be sent in 2 waves: first a header indicating the msg length,
        and then the message itself
        """
        # format as json string and then convert to bytes
        formattedMsg = json.dumps(results).encode()

        # build then send header with info about msg length
        hdr = '{:d}\n'.format(len(formattedMsg))
        connection.send(hdr.encode())

        # send results as formatted message
        connection.sendall(formattedMsg)
        print('Sent result: {}'.format(formattedMsg))

    def killServer(self):
        self.alive = False


def launchPynealSim(TR=1, resultsServerPort=5556):
    """
    Start the results server going on its own thread where it will listen for
    incoming responses, and then send a response to each request.

    Meanwhile, start sending fake results to the resultsServer at a rate set
    by the TR
    """
    # Results Server Thread, listens for requests from end-user (e.g. task
    # presentation), and sends back results
    settings = {'resultsServerPort':resultsServerPort}
    resultsServer = ResultsServer(settings)
    resultsServer.daemon = True
    resultsServer.start()
    print('Starting Results Server...')


    # Start making up fake results
    for volIdx in range(500):
        # generate a random value
        avgActivation = np.around(np.random.normal(loc=2432, scale=10), decimals=2)
        result = {'Average': avgActivation}

        # send result to the resultsServer
        resultsServer.updateResults(volIdx, result)

        # pause for TR
        time.sleep(TR)


if __name__ == '__main__':
    launchPynealSim(TR=1, resultsServerPort=5556)
