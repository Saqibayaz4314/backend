import traceback
import os
try:
    from utils.firebase_client import FirebaseClient
    client = FirebaseClient()
    print('SDK Connected:', client.is_connected())
    print('Mock:', client.use_mock)
    has_access = client.has_firestore_access()
    print('Firestore Access:', has_access)

    if has_access:
        print("Testing write/read...")
        saved = client.save_incident("test_doc_123", {"status": "ok"})
        doc = client.get_incident("test_doc_123")
        print("Write OK:", saved)
        print("Read doc:", doc)
        print("FINAL STATUS: FIREBASE WORKING")
    else:
        print("FINAL STATUS: FIREBASE NOT WORKING (Auth/permission/credentials issue)")
except Exception as e:
    print(traceback.format_exc())
