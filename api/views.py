from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from core.settings import db
import random

# MongoDB Collections
companies_col = db["companies"]
credentials_col = db["credentials"]

# Helper: Seed default companies and credentials if MongoDB collections are empty
def seed_default_data_if_needed():
    try:
        if companies_col.count_documents({}) == 0:
            default_companies = [
                {
                    "company_id": "4777",
                    "companyName": "Tech BRJ",
                    "companySlug": "tech-brj",
                    "username": "techbrj",
                    "password": "techbrj.india"
                },
                {
                    "company_id": "1002",
                    "companyName": "Aryan Personal",
                    "companySlug": "aryan-personal",
                    "username": "admin",
                    "password": "admin"
                }
            ]
            companies_col.insert_many(default_companies)

        if credentials_col.count_documents({}) == 0:
            default_credentials = [
                {
                    "company_id": "4777",
                    "credentials": [
                        {
                            "id": "2001",
                            "projectName": "Ops Portals",
                            "username": "alex",
                            "mobile": "+91 9876543210",
                            "password": "P@ssw0rd!",
                            "link": "https://ops.verdantlabs.com"
                        }
                    ]
                },
                {
                    "company_id": "1002",
                    "credentials": [
                        {
                            "id": "2002",
                            "projectName": "Client Vault",
                            "username": "nina",
                            "mobile": "+91 9123456789",
                            "password": "Moss@2024",
                            "link": "https://vault.mossco.com"
                        }
                    ]
                }
            ]
            credentials_col.insert_many(default_credentials)
    except Exception as e:
        print(f"Seed info: {e}")

# Call seed on module load
seed_default_data_if_needed()


# Helper: Generate a unique 4-digit ID
def generate_id(existing_ids):
    while True:
        candidate = str(random.randint(1000, 9999))
        if candidate not in existing_ids:
            return candidate


# ----------------------------------------------------
# AUTHENTICATION ENDPOINT
# ----------------------------------------------------
@api_view(['POST'])
def login(request):
    username = (request.data.get('username') or '').strip()
    password = (request.data.get('password') or '').strip()

    if not username or not password:
        return Response(
            {
                'success': False,
                'message': 'Please provide both username and password.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    company = companies_col.find_one({'username': username.lower(), 'password': password})

    if not company:
        return Response(
            {
                'success': False,
                'message': 'The provided credentials are invalid.'
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    return Response(
        {
            'success': True,
            'message': 'Login successful.',
            'company': {
                'id': company.get('company_id'),
                'name': company.get('companyName'),
                'slug': company.get('companySlug')
            }
        },
        status=status.HTTP_200_OK
    )


# ----------------------------------------------------
# CREDENTIALS CRUD ENDPOINTS (GET, POST, PUT, DELETE)
# ----------------------------------------------------
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def manage_credentials(request, company_id):
    # 1. GET ALL CREDENTIALS FOR A COMPANY
    if request.method == 'GET':
        doc = credentials_col.find_one({'company_id': str(company_id)})
        items = doc.get('credentials', []) if doc else []
        
        # Strip BSON ObjectId for JSON serialization
        clean_items = []
        for item in items:
            item_copy = dict(item)
            item_copy.pop('_id', None)
            clean_items.append(item_copy)
            
        return Response(clean_items, status=status.HTTP_200_OK)

    # 2. POST: CREATE NEW CREDENTIAL
    elif request.method == 'POST':
        projectName = (request.data.get('projectName') or '').strip()
        username = (request.data.get('username') or '').strip()
        mobile = (request.data.get('mobile') or '').strip()
        password = (request.data.get('password') or '').strip()
        link = (request.data.get('link') or '').strip()

        if not projectName:
            return Response({'message': 'Project Name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        doc = credentials_col.find_one({'company_id': str(company_id)})
        existing_items = doc.get('credentials', []) if doc else []
        existing_ids = {str(item.get('id')) for item in existing_items}

        new_item = {
            'id': generate_id(existing_ids),
            'projectName': projectName,
            'username': username,
            'mobile': mobile,
            'password': password,
            'link': link
        }

        credentials_col.update_one(
            {'company_id': str(company_id)},
            {'$push': {'credentials': new_item}},
            upsert=True
        )

        return Response(new_item, status=status.HTTP_201_CREATED)

    # 3. PUT: UPDATE EXISTING CREDENTIAL
    elif request.method == 'PUT':
        item_id = request.data.get('id')
        if not item_id:
            return Response({'message': 'Credential ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        updated_item = {
            'id': str(item_id),
            'projectName': (request.data.get('projectName') or '').strip(),
            'username': (request.data.get('username') or '').strip(),
            'mobile': (request.data.get('mobile') or '').strip(),
            'password': (request.data.get('password') or '').strip(),
            'link': (request.data.get('link') or '').strip()
        }

        result = credentials_col.update_one(
            {'company_id': str(company_id), 'credentials.id': str(item_id)},
            {'$set': {'credentials.$': updated_item}}
        )

        if result.matched_count == 0:
            # Fallback if document structure doesn't match
            credentials_col.update_one(
                {'company_id': str(company_id)},
                {'$push': {'credentials': updated_item}},
                upsert=True
            )

        return Response(updated_item, status=status.HTTP_200_OK)

    # 4. DELETE: REMOVE CREDENTIAL
    elif request.method == 'DELETE':
        item_id = request.data.get('id')
        if not item_id:
            return Response({'message': 'Credential ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        result = credentials_col.update_one(
            {'company_id': str(company_id)},
            {'$pull': {'credentials': {'id': str(item_id)}}}
        )

        return Response({'message': 'Credential deleted successfully.'}, status=status.HTTP_200_OK)


# ----------------------------------------------------
# MONGO DB HEALTH CHECK ENDPOINT
# ----------------------------------------------------
@api_view(['GET'])
def test_connection(request):
    try:
        collections = db.list_collection_names()
        return Response({
            'status': 'success',
            'message': 'MongoDB Atlas connection established successfully.',
            'database': db.name,
            'collections': collections
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)