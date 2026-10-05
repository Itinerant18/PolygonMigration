from django.shortcuts import render
from .polygon_api import PolygonAPI
from .models import Problem, SampleTestCase, ProblemTestCase, ProblemTag
from django.utils.text import slugify
from django.db.models import Q
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
import re
import lxml.html
import logging
import json
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction

logger = logging.getLogger(__name__)

def parse_problem_html(html_content):
    """
    Parses a Polygon problem.html content and extracts key fields such as title, legend, input/output formats, and notes.

    Args:
        html_content (str): The HTML content of the problem.html file.

    Returns:
        dict: A dictionary containing the extracted fields:
            - title (str): The problem title.
            - legend (str): The problem statement/legend HTML.
            - input_format (str): The input specification HTML.
            - output_format (str): The output specification HTML.
            - notes (str): The notes HTML (if present).
    """
    logger.info('Entered parse_problem_html with content length=%d', len(html_content))
    tree = lxml.html.fromstring(html_content)

    def get_div_inner_html(tree, class_name, skip_section_title=False):
        """
        Extracts the inner HTML of a div with a given class name from the lxml tree.

        Args:
            tree (lxml.html.HtmlElement): The parsed HTML tree.
            class_name (str): The class name of the div to extract.
            skip_section_title (bool): If True, skips the first child div with class 'section-title'.

        Returns:
            str: The concatenated inner HTML of the div's children, or an empty string if not found.
        """
        div = tree.xpath(f'//div[@class="{class_name}"]')
        if not div:
            return ''
        div = div[0]
        # Get all children as HTML
        children = div.getchildren()
        html_parts = []
        for child in children:
            # For input/output, skip the first section-title div if requested
            if skip_section_title and child.tag == 'div' and 'section-title' in child.get('class', ''):
                continue
            html_parts.append(lxml.html.tostring(child, encoding='unicode'))
        content = ''.join(html_parts).strip()
        # Remove leading <p></p> tags
        content = re.sub(r'^(<p>\s*</p>)+', '', content)
        return content

    legend = get_div_inner_html(tree, 'legend')
    input_format = get_div_inner_html(tree, 'input-specification', skip_section_title=True)
    output_format = get_div_inner_html(tree, 'output-specification', skip_section_title=True)

    # Title extraction
    title = ''
    title_div = tree.xpath('//div[@class="title"]')
    if title_div:
        title = title_div[0].text_content().strip()

    notes = get_div_inner_html(tree, 'note', skip_section_title=True)

    logger.debug('Extracted title=%s, legend length=%d, input_format length=%d, output_format length=%d', title, len(legend), len(input_format), len(output_format))
    logger.info('Exiting parse_problem_html')
    return {
        'title': title,
        'legend': legend,
        'input_format': input_format,
        'output_format': output_format,
        'notes': notes,
    }

@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='/users/login/')
def index(request):
    """
    Main view for the problem migration interface. Handles GET and POST requests for migrating problems and test cases
    between Polygon, the local database, and Google Drive.

    Handles the following POST actions:
        - Fetches and displays problem info from Polygon.
        - Migrates problem data to the database.
        - Migrates test cases to the database.
        - Uploads test cases to Google Drive.

    Args:
        request (HttpRequest): The incoming HTTP request.

    Returns:
        HttpResponse: The rendered index.html template with context data.
    """
    logger.info('Entered index view with method=%s', request.method)
    context = {}
    
    # Get all existing tags for the dropdown
    all_tags = ProblemTag.objects.all().order_by('tag_name')
    context['all_tags'] = all_tags
    
    # Serialize tags for JavaScript
    context['all_tags_json'] = json.dumps([{
        'pk': tag.id,
        'fields': {'name': tag.tag_name}
    } for tag in all_tags])
    
    # Initialize selected_tags if not set
    if 'selected_tags' not in context:
        context['selected_tags'] = []
    context['selected_tags_json'] = json.dumps(context['selected_tags'])
    
    if request.method == 'POST':
        polygon_id = request.POST.get('problem_id')
        migrate_to_drive = request.POST.get('migrate_to_drive')
        migrate_to_db = request.POST.get('migrate_to_db')
        migrate_test_cases_to_db = request.POST.get('migrate_test_cases_to_db')
        difficulty = request.POST.get('difficulty', '')
        selected_tags = request.POST.getlist('tags')  # Get selected tags
        new_tag = request.POST.get('new_tag', '').strip()  # Get new tag input
        
        logger.debug('POST data: polygon_id=%s, migrate_to_drive=%s, migrate_to_db=%s, migrate_test_cases_to_db=%s, difficulty=%s, selected_tags=%s, new_tag=%s', 
                    polygon_id, migrate_to_drive, migrate_to_db, migrate_test_cases_to_db, difficulty, selected_tags, new_tag)
        logger.debug('All POST data: %s', dict(request.POST))
        context['difficulty'] = difficulty
        context['selected_tags'] = selected_tags
        context['new_tag'] = new_tag
        
        if polygon_id:
            logger.info('Processing polygon_id=%s', polygon_id)
            api = PolygonAPI()
            context['problem_id'] = polygon_id
            
            # Always check if the problem exists in the database for display logic
            db_problem = Problem.objects.filter(polygon_id=polygon_id).first()
            logger.debug('db_problem=%s', db_problem)
            
            if db_problem:
                context['db_problem'] = db_problem
                # Always show the tags currently attached to the problem
                context['selected_tags'] = [tag.tag_name for tag in db_problem.extra_tags.all()]
                # Fetch the difficulty from the database if present
                context['difficulty'] = db_problem.difficulty
                # Also fetch main solution if not already set
                if 'main_solution' not in context:
                    main_solution = None
                    try:
                        # Get solutions using Polygon API
                        update_working_copy = api._make_request('problem.updateWorkingCopy', {'problemId': polygon_id})
                        logger.debug('Updated working copy: %s', update_working_copy)
                        solutions = api._make_request('problem.solutions', {'problemId': polygon_id})
                        logger.debug('Fetched solutions: %s', solutions)
                        if solutions:
                            # Look for main solution (tag 'MA') first, then any other solution
                            main_solution_name = None
                            for solution in solutions:
                                if solution.get('tag') == 'MA':  # Main solution
                                    main_solution_name = solution['name']
                                    break
                            if not main_solution_name and solutions:
                                # If no main solution found, use the first available solution
                                main_solution_name = solutions[0]['name']
                            
                            if main_solution_name:
                                # Get the solution content
                                main_solution = api._make_plain_request('problem.viewSolution', {
                                    'problemId': polygon_id,
                                    'name': main_solution_name
                                })
                    except Exception as e:
                        logger.error('Error fetching solution: %s', e)
                        main_solution = None
                    context['main_solution'] = main_solution
            
            try:
                with transaction.atomic():
                    # Azure upload disabled. Google Drive is used for storage now.
                    # Old Azure migration block kept for reference:
                    # migrate_to_azure = request.POST.get('migrate_to_azure')
                    # AZURE_STORAGE_ACCOUNT_URL = settings.AZURE_STORAGE_ACCOUNT_URL
                    # AZURE_TENANT_ID = settings.AZURE_TENANT_ID
                    # AZURE_CLIENT_ID = settings.AZURE_CLIENT_ID
                    # AZURE_USERNAME = settings.AZURE_USERNAME
                    # AZURE_PASSWORD = settings.AZURE_PASSWORD
                    # AZURE_CONTAINER_NAME = settings.AZURE_CONTAINER_NAME
                    # api.migrate_to_azure_blob(polygon_id, AZURE_STORAGE_ACCOUNT_URL, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_USERNAME, AZURE_PASSWORD, AZURE_CONTAINER_NAME, problem_id)
                    if migrate_to_drive:
                        problem_obj = Problem.objects.filter(polygon_id=polygon_id).first()
                        if not problem_obj:
                            context['error'] = f"Problem with Polygon ID {polygon_id} has not been migrated to the database yet. Please migrate the problem to the database first before uploading test cases to Google Drive."
                            return render(request, 'problems/index.html', context)

                        if not settings.GOOGLE_DRIVE_UPLOAD_ENABLED:
                            context['error'] = "Google Drive upload is disabled."
                            return render(request, 'problems/index.html', context)

                        if not settings.GOOGLE_DRIVE_FOLDER_ID:
                            context['error'] = "Google Drive folder is not configured."
                            return render(request, 'problems/index.html', context)

                        from .google_drive import input_filename, output_filename, upload_text_file

                        drive_cases = api.get_test_cases_from_redis(polygon_id)
                        if drive_cases is None:
                            drive_cases = api.get_all_test_cases(polygon_id)
                            api.store_test_cases_in_redis(polygon_id, drive_cases, expiry_hours=0.5)

                        uploaded = 0
                        failed = 0
                        for idx, test in enumerate(drive_cases, start=1):
                            try:
                                input_data = test.get('input', '') or ''
                                output_data = test.get('output', '') or ''
                                input_name = input_filename(problem_obj.id, idx)
                                output_name = output_filename(problem_obj.id, idx)
                                input_id = upload_text_file(input_name, input_data)
                                output_id = upload_text_file(output_name, output_data)
                                tc = ProblemTestCase.objects.filter(problem=problem_obj, order=idx).first()
                                if tc:
                                    tc.drive_input_file_id = input_id
                                    tc.drive_output_file_id = output_id
                                    tc.save()
                                uploaded += 1
                            except Exception:
                                logger.warning('Google Drive upload failed for test case %s', idx)
                                failed += 1

                        if failed:
                            context['error'] = "Upload failed for %s test cases." % failed
                        if uploaded:
                            context['success'] = "%s test cases uploaded to Google Drive." % uploaded
                        if not uploaded and failed:
                            raise Exception(context['error'])
                    
                    # Always fetch problem data for display
                    info = api.get_problem_info(polygon_id)
                    logger.debug('Polygon problem info: %s', info)
                    
                    # Download and extract the problem package, then parse problem.html
                    problem_html_content = api.download_and_extract_package(polygon_id)
                    logger.debug('Downloaded and extracted problem_html_content, length: %d', len(problem_html_content))
                    html_data = parse_problem_html(problem_html_content)
                    logger.debug('Parsed html_data: %s', html_data)
                    

                    # Fetch all test cases for display
                    all_test_cases = []
                    if(migrate_to_db or migrate_test_cases_to_db or migrate_to_drive):
                        all_test_cases=api.get_test_cases_from_redis(polygon_id)
                        if all_test_cases is None:
                            logger.warning('Test cases not found in Redis, fetching from Polygon')
                            all_test_cases = api.get_all_test_cases(polygon_id)
                            api.store_test_cases_in_redis(polygon_id, all_test_cases, expiry_hours=0.5)
                        else:
                            logger.info('Retrieved test cases from Redis for test case migration to DB (saved Polygon API call)')
                    else:
                        all_test_cases = api.get_all_test_cases(polygon_id)
                        logger.debug('Fetched all test cases.')
                        # Store test cases in Redis for this platform (30 minutes expiry)
                        api.store_test_cases_in_redis(polygon_id, all_test_cases, expiry_hours=0.5)
                        
                    
                    # Prepare test cases for display with truncated content
                    display_test_cases = []
                    for test_case in all_test_cases:
                        input_data = test_case.get('input', '')
                        output_data = test_case.get('output', '')
                        description = test_case.get('description', '')
                        
                        display_test_cases.append({
                            'index': test_case.get('index', ''),
                            'input_preview': input_data[:50] + ('...' if len(input_data) > 50 else ''),
                            'output_preview': output_data[:50] + ('...' if len(output_data) > 50 else ''),
                            'description_preview': description[:50] + ('...' if len(description) > 50 else ''),
                            'is_sample': test_case.get('is_sample', False),
                            'full_input': input_data,
                            'full_output': output_data,
                            'full_description': description,
                        })
                    
                    context['all_test_cases'] = display_test_cases
                    
                    # Prepare problem data for display
                    title = html_data['title'] or info.get('name', f'Polygon Problem {polygon_id}')
                    slug = slugify(title)
                    problem_statement = html_data['legend']
                    input_format = html_data['input_format']
                    output_format = html_data['output_format']
                    constraints = ''
                    editorial = ''
                    time_limit = info.get('timeLimit', 1000)
                    memory_limit = info.get('memoryLimit', 256)
                    checker_type = api._make_request('problem.checker', {'problemId': polygon_id}) or 'ncmp'
                    logger.debug('checker_type=%s', checker_type)
                    if checker_type.startswith('std::'):
                        checker_type = checker_type[5:]
                    if checker_type.endswith('.cpp'):
                        checker_type = checker_type[:-4]
                    
                    # Check if checker is valid (in CHECKER_TYPE_CHOICES)
                    valid_checkers = ['ncmp', 'fcmp', 'hcmp', 'lcmp', 'nyesno', 'rcmp4', 'rcmp6', 'rcmp9', 'wcmp', 'yesno']
                    if checker_type not in valid_checkers:
                        checker_type = 'custom'
                        # context['info'] = f"Custom checker detected. Please reach out to dev team."
                    
                    # Get custom checker info for display
                    custom_checker_info = api.get_custom_checker_info(polygon_id)
                    
                    test_case_count = len(api.get_test_cases(polygon_id))
                    logger.debug('test_case_count=%d', test_case_count)
                    
                    # Store fetched data in context for display (without database operations)
                    notes = html_data['notes']
                    context['fetched_problem'] = {
                        'polygon_id': polygon_id,
                        'title': title,
                        'slug': slug,
                        'difficulty': difficulty,
                        'problem_statement': problem_statement,
                        'input_format': input_format,
                        'output_format': output_format,
                        'constraints': constraints,
                        'editorial': editorial,
                        'time_limit': time_limit,
                        'memory_limit': memory_limit,
                        'checker_type': checker_type,
                        'custom_checker_info': custom_checker_info,
                        'test_case_count': test_case_count,
                        'notes': notes,
                    }
                    
                    # Handle database migration
                    if migrate_to_db:
                        # Validate that difficulty is provided
                        if not difficulty:
                            context['error'] = "Please select a difficulty level before migrating to database."
                            raise Exception(context['error'])
                        
                        # Try to find an existing Problem by polygon_id or by ProblemTag name matching the title
                        logger.info('Starting DB migration for polygon_id=%s', polygon_id)
                        problem_obj = Problem.objects.filter(Q(polygon_id=polygon_id)).first()
                        if problem_obj:
                            logger.info('Updating existing Problem in DB')
                            # Update the existing Problem
                            problem_obj.title = title
                            problem_obj.slug = slug
                            problem_obj.difficulty = difficulty 
                            problem_obj.problem_statement = problem_statement
                            problem_obj.input_format = input_format
                            problem_obj.output_format = output_format
                            problem_obj.constraints = constraints
                            problem_obj.editorial = editorial
                            problem_obj.time_limit = time_limit
                            problem_obj.memory_limit = memory_limit
                            problem_obj.checker_type = checker_type
                            problem_obj.test_case_count = test_case_count
                            problem_obj.polygon_id = polygon_id
                            problem_obj.notes = notes  
                            problem_obj.save()
                            context['db_success'] = "Problem saved to database."

                        else:
                            # Create a new Problem entry
                            logger.info('Creating new Problem in DB')
                            problem_obj = Problem.objects.create(
                                polygon_id=polygon_id,
                                title=title,
                                slug=slug,
                                difficulty=difficulty,
                                problem_statement=problem_statement,
                                input_format=input_format,
                                output_format=output_format,
                                constraints=constraints,
                                editorial=editorial,
                                time_limit=time_limit,
                                memory_limit=memory_limit,
                                checker_type=checker_type,
                                test_case_count=test_case_count,
                                notes=notes,
                            )
                            context['db_success'] = "Problem saved to database."

                        # Handle tags
                        logger.info('Processing tags for problem')
                        logger.debug('Selected tags before processing: %s', selected_tags)
                        logger.debug('New tag before processing: %s', new_tag)
                        
                        # Clear existing tags
                        problem_obj.extra_tags.clear()
                        logger.debug('Cleared existing tags for problem %s', problem_obj.id)
                        
                        # Process selected tags
                        for tag_name in selected_tags:
                            if tag_name.strip():
                                logger.debug('Processing tag: %s', tag_name)
                                tag, created = ProblemTag.objects.get_or_create(tag_name=tag_name.strip())
                                problem_obj.extra_tags.add(tag)
                                if created:
                                    logger.info('Created new tag: %s', tag_name)
                                else:
                                    logger.debug('Added existing tag: %s', tag_name)
                        
                        # Process new tag if provided
                        if new_tag:
                            logger.debug('Processing new tag: %s', new_tag)
                            new_tag_obj, created = ProblemTag.objects.get_or_create(tag_name=new_tag)
                            problem_obj.extra_tags.add(new_tag_obj)
                            if created:
                                logger.info('Created new tag from input: %s', new_tag)
                            else:
                                logger.debug('Added existing tag from input: %s', new_tag)
                        
                        # Update context with current tags for display
                        final_tags = [tag.tag_name for tag in problem_obj.extra_tags.all()]
                        context['selected_tags'] = final_tags
                        logger.debug('Final tags after processing: %s', final_tags)

                        # Get test cases from Redis instead of fetching from Polygon again
                        test_cases = api.get_test_cases_from_redis(polygon_id)
                        if test_cases is None:
                            # Fallback to fetching from Polygon if not in Redis
                            logger.warning('Test cases not found in Redis, fetching from Polygon')
                            test_cases = api.get_all_test_cases(polygon_id)
                            # Store them in Redis for future use
                            api.store_test_cases_in_redis(polygon_id, test_cases, expiry_hours=0.5)
                        else:
                            logger.info('Retrieved test cases from Redis for test case migration to DB (saved Polygon API call)')
                        
                        logger.debug('test_cases for DB migration.')

                        # Update or create sample test cases
                        sample_tests = [test for test in test_cases if test.get('is_sample', False)]
                        logger.debug('sample_tests: %s', sample_tests)
                        existing_sample_cases = list(SampleTestCase.objects.filter(problem=problem_obj).order_by('order'))
                        order = 1
                        for idx, test in enumerate(sample_tests):
                            input_data = test.get('input', '').rstrip()
                            output_data = test.get('output', '').rstrip()
                            logger.debug('Sample test idx=%d, input_data=%s, output_data=%s', idx, input_data[:50] + ('...' if len(input_data) > 50 else ''), output_data[:50] + ('...' if len(output_data) > 50 else ''))
                            if input_data and output_data:
                                if idx < len(existing_sample_cases):
                                    # Update existing sample test case
                                    stc = existing_sample_cases[idx]
                                    stc.input = input_data
                                    stc.output = output_data
                                    stc.order = order
                                    stc.save()
                                else:
                                    # Create new sample test case
                                    SampleTestCase.objects.create(
                                        problem=problem_obj,
                                        input=input_data,
                                        output=output_data,
                                        order=order
                                    )
                                order += 1

                        # Fetch the Problem entry from the database to display
                        db_problem = Problem.objects.get(pk=problem_obj.pk)
                        context['db_problem'] = db_problem

                        # Fetch main correct solution from Polygon if possible
                        main_solution = None
                        try:
                            # Get solutions using Polygon API
                            solutions = api._make_request('problem.solutions', {'problemId': polygon_id})
                            logger.debug('Fetched solutions: %s', solutions)
                            if solutions:
                                # Look for main solution (tag 'MA') first, then any other solution
                                main_solution_name = None
                                for solution in solutions:
                                    if solution.get('tag') == 'MA':  # Main solution
                                        main_solution_name = solution['name']
                                        break
                                if not main_solution_name and solutions:
                                    # If no main solution found, use the first available solution
                                    main_solution_name = solutions[0]['name']
                                
                                if main_solution_name:
                                    # Get the solution content
                                    main_solution = api._make_plain_request('problem.viewSolution', {
                                        'problemId': polygon_id,
                                        'name': main_solution_name
                                    })
                        except Exception as e:
                            logger.error('Error fetching solution: %s', e)
                            main_solution = None
                        context['main_solution'] = main_solution

                    if migrate_test_cases_to_db:
                        problem_obj = Problem.objects.filter(polygon_id=polygon_id).first()
                        if not problem_obj:
                            context['error'] = "Please migrate the problem to the database first."
                            raise Exception(context['error'])

                        test_cases = api.get_test_cases_from_redis(polygon_id)
                        if test_cases is None:
                            test_cases = api.get_all_test_cases(polygon_id)
                            api.store_test_cases_in_redis(polygon_id, test_cases, expiry_hours=0.5)

                        fetched = len(test_cases)
                        # Keep Drive file IDs so re-migrating test cases
                        # does not lose the Drive upload links.
                        old_drive_ids = {
                            tc.order: (tc.drive_input_file_id, tc.drive_output_file_id)
                            for tc in ProblemTestCase.objects.filter(problem=problem_obj)
                        }
                        ProblemTestCase.objects.filter(problem=problem_obj).delete()

                        saved = 0
                        for order, test in enumerate(test_cases, start=1):
                            drive_ids = old_drive_ids.get(order, (None, None))
                            ProblemTestCase.objects.create(
                                problem=problem_obj,
                                is_sample=test.get('is_sample', False),
                                input=test.get('input', '') or '',
                                output=test.get('output', '') or '',
                                description=test.get('description', ''),
                                order=order,
                                drive_input_file_id=drive_ids[0],
                                drive_output_file_id=drive_ids[1],
                            )
                            saved += 1

                        if saved != fetched:
                            context['error'] = "Warning: only %s of %s test cases saved to database." % (saved, fetched)
                        else:
                            context['success'] = "%s test cases saved to database." % saved

            except Exception as e:
                logger.error('Exception in index view: %s', e, exc_info=True)
                if 'success' not in context and 'error' not in context:
                    context['error'] = "Migration failed and all changes have been rolled back."
                api.clear_test_cases_from_redis(polygon_id)

    # Update selected_tags_json after all context updates
    if 'selected_tags' in context:
        context['selected_tags_json'] = json.dumps(context['selected_tags'])
    else:
        context['selected_tags_json'] = json.dumps([])

    logger.info('Exiting index view')
    return render(request, 'problems/index.html', context)

