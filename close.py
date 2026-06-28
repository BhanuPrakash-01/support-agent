import sys
from memory import close_ticket

ticket_id = int(sys.argv[1])
resolution = sys.argv[2]
close_ticket(ticket_id, resolution)
print(f"Closed ticket {ticket_id} and updated the customer's summary.")