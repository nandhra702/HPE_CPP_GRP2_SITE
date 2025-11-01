from django.core.management.base import BaseCommand
from judge.models.emailing import EmailTemplate


class Command(BaseCommand):
    help = 'Creates default email templates for HPE Hackathon platform'

    def handle(self, *args, **options):
        templates_data = [
            {
                'name': 'HPE Hackathon Registration Invitation',
                'subject': 'Join the HPE Hackathon Platform - Registration Open!',
                'body': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>HPE Hackathon Registration</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #01A982; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .cta-button { 
            display: inline-block; 
            background-color: #01A982; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 20px 0; 
        }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 HPE Hackathon Registration</h1>
        </div>
        <div class="content">
            <h2>You're Invited to Join the HPE Hackathon Platform!</h2>
            
            <p>Dear Participant,</p>
            
            <p>We're excited to invite you to register for the <strong>HPE Hackathon Platform</strong> - your gateway to innovation, collaboration, and amazing prizes!</p>
            
            <h3>🎯 What Awaits You:</h3>
            <ul>
                <li><strong>Cutting-edge Challenges</strong> - Solve real-world problems with HPE technologies</li>
                <li><strong>Expert Mentorship</strong> - Get guidance from HPE engineers and industry leaders</li>
                <li><strong>Amazing Prizes</strong> - Win exciting rewards and recognition</li>
                <li><strong>Networking Opportunities</strong> - Connect with like-minded innovators</li>
                <li><strong>Skill Development</strong> - Enhance your technical and problem-solving abilities</li>
            </ul>
            
            <h3>🔥 Ready to Get Started?</h3>
            <p>Registration is now open! Secure your spot and be part of this incredible journey.</p>
            
            <div style="text-align: center;">
                <a href="https://your-hackathon-platform.com/register" class="cta-button">Register Now</a>
            </div>
            
            <h3>📅 Important Dates:</h3>
            <ul>
                <li><strong>Registration Opens:</strong> Now</li>
                <li><strong>Registration Closes:</strong> [Insert Date]</li>
                <li><strong>Hackathon Dates:</strong> [Insert Dates]</li>
            </ul>
            
            <p><strong>Don't miss out on this opportunity to innovate, learn, and compete!</strong></p>
            
            <p>Questions? Feel free to reach out to our support team at <a href="mailto:support@hpe-hackathon.com">support@hpe-hackathon.com</a></p>
            
            <p>Looking forward to seeing your innovative solutions!</p>
            
            <p>Best regards,<br>
            <strong>The HPE Hackathon Team</strong></p>
        </div>
        <div class="footer">
            <p>© 2025 HPE Hackathon Platform. All rights reserved.</p>
            <p>This email was sent to {{ email }}. If you believe this was sent in error, please contact us.</p>
        </div>
    </div>
</body>
</html>''',
                'is_html': True,
                'is_active': True,
            },
            {
                'name': 'Contest Reminder - Join Now',
                'subject': 'Don\'t Miss Out! Contest Starting Soon - Join Now',
                'body': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Contest Reminder</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #FF6B35; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .urgency { background-color: #FFE5E5; padding: 15px; border-left: 4px solid #FF6B35; margin: 15px 0; }
        .cta-button { 
            display: inline-block; 
            background-color: #FF6B35; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 20px 0;
            font-weight: bold;
        }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
        .countdown { background-color: #FF6B35; color: white; padding: 10px; text-align: center; font-size: 18px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ Contest Starting Soon!</h1>
        </div>
        <div class="countdown">
            Contest Registration Closes Soon!
        </div>
        <div class="content">
            <h2>Last Chance to Join the Contest!</h2>
            
            <p>Hello {{ name|default:"Participant" }},</p>
            
            <div class="urgency">
                <strong>⚡ URGENT REMINDER:</strong> The contest registration is closing soon! Don't miss your chance to participate in this exciting competition.
            </div>
            
            <h3>🏆 What You're Missing:</h3>
            <ul>
                <li><strong>Exciting Challenges</strong> - Test your skills against challenging problems</li>
                <li><strong>Competitive Environment</strong> - Compete with talented participants from around the world</li>
                <li><strong>Real-time Rankings</strong> - See how you stack up against other contestants</li>
                <li><strong>Prizes & Recognition</strong> - Win amazing rewards for top performances</li>
                <li><strong>Learning Experience</strong> - Improve your problem-solving skills</li>
            </ul>
            
            <h3>📊 Contest Details:</h3>
            <ul>
                <li><strong>Contest Name:</strong> {{ contest_name|default:"HPE Programming Contest" }}</li>
                <li><strong>Start Time:</strong> {{ start_time|default:"[Insert Start Time]" }}</li>
                <li><strong>Duration:</strong> {{ duration|default:"3 hours" }}</li>
                <li><strong>Problems:</strong> {{ problem_count|default:"5-8" }} challenging problems</li>
                <li><strong>Languages:</strong> C++, Java, Python, and more</li>
            </ul>
            
            <div class="urgency">
                <p><strong>⏱️ Time is Running Out!</strong></p>
                <p>Registration closes in just a few hours. Register now to secure your spot!</p>
            </div>
            
            <div style="text-align: center;">
                <a href="https://your-platform.com/contest/join" class="cta-button">Join Contest Now!</a>
            </div>
            
            <h3>🎯 Tips for Success:</h3>
            <ul>
                <li>Review algorithm fundamentals</li>
                <li>Practice with similar problems</li>
                <li>Ensure stable internet connection</li>
                <li>Prepare your development environment</li>
                <li>Read problem statements carefully during contest</li>
            </ul>
            
            <p><strong>Still have questions?</strong> Check out our <a href="https://your-platform.com/help">contest guidelines</a> or contact support at <a href="mailto:contest-support@platform.com">contest-support@platform.com</a></p>
            
            <p>We can't wait to see your solutions in action!</p>
            
            <p>Good luck and happy coding!</p>
            
            <p>Best regards,<br>
            <strong>The Contest Team</strong></p>
        </div>
        <div class="footer">
            <p>© 2025 Contest Platform. All rights reserved.</p>
            <p>This reminder was sent to {{ email }}. Manage your email preferences <a href="#">here</a>.</p>
        </div>
    </div>
</body>
</html>''',
                'is_html': True,
                'is_active': True,
            }
        ]
        
        created_count = 0
        for template_data in templates_data:
            template, created = EmailTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: "{template.name}"')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template already exists: "{template.name}"')
                )
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} email template(s)')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No new templates were created (all already exist)')
            )