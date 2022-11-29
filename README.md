# Proxy-Server
The file "proxy.py" contains the code that i have written to simulate a proxy server.

Steps to run proxy server

1. Run the following command 
   * python3 proxy.py <desired-port> <image-flag> <attack-flag>


2. With the desired port set, make sure the network settings on Mozilla Firefox is set to the following,
    * HTTP IP proxy : The ip address of the platform hosting the proxy server
    * Port Number : desired port (Note that the desired port number should be > 1024 and <= 65535)

3. Use “Ctrl + C”, to stop the proxy server from running.

On top of being a proxy server that forwards html request and replies between host and actual web servers. The code also allows for the calculations of telemetry of a webpage and do note that the proxy server is written with multi-threading.
