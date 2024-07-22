from celery import shared_task
from twisted.internet import reactor
from jasmin.routing.proxies import RouterPBProxy
from jasmin.routing.jasminApi import Group
from twisted.internet.defer import Deferred


@shared_task
def perform_operations_task(gid):
    # This function will be executed in the Celery worker
    def twisted_task():
        # Create an instance of RouterPBProxy
        instance = RouterPBProxy()

        def on_connect(result):
            # Define what to do once the connection is established
            group = Group(gid)
            d = instance.group_add(group)
            d.addCallback(on_group_added)
            d.addErrback(on_error)

        def on_group_added(result):
            print(f"Group {gid} added successfully:", result)
            reactor.callFromThread(lambda: reactor.stop())  # Stop the reactor

        def on_error(failure):
            print(f"An error occurred while adding group {gid}:", failure)
            reactor.callFromThread(lambda: reactor.stop())  # Stop the reactor

        def connect_and_add_group():
            d = instance.connect('127.0.0.1', 8988, 'radmin', 'rpwd')
            d.addCallback(on_connect)
            d.addErrback(on_error)

        reactor.callInThread(connect_and_add_group)

    reactor.callFromThread(twisted_task)
    if not reactor.running:
        reactor.run()


